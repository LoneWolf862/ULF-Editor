"""ULF FCH binary engine for legacy saves and Valheim 1.0.21.
Rebuilds inventory and skills only, preserving other profile/player sections byte-for-byte.
"""
import hashlib
import struct
import copy
import math
import re
from core.catalog import CATALOG
from dataclasses import dataclass, field

class FormatError(ValueError): pass

class Reader:
    def __init__(self,b): self.b=b;self.p=0
    def read(self,n):
        if n<0 or self.p+n>len(self.b):raise FormatError('Truncated or invalid save')
        t=self.b[self.p:self.p+n];self.p+=n;return t
    def num(self,f):return struct.unpack('<'+f,self.read(struct.calcsize('<'+f)))[0]
    def u8(self):return self.num('B')
    def i32(self):return self.num('i')
    def u16(self):return self.num('H')
    def i64(self):return self.num('q')
    def f32(self):return self.num('f')
    def var(self):
        n=0
        for i in range(5):
            x=self.u8();n|=(x&127)<<(i*7)
            if not x&128:return n
        raise FormatError('Invalid variable-length integer')
    def count(self, maximum=100000):
        value=self.i32()
        if not 0<=value<=maximum:raise FormatError('A save section has an invalid entry count')
        return value
    def string(self):
        length=self.var()
        if length>16*1024*1024:raise FormatError('A save string exceeds the supported size')
        try:return self.read(length).decode('utf-8')
        except UnicodeDecodeError as error:raise FormatError('A save string contains invalid text') from error
    def arr(self):return self.read(self.i32())
    def vector(self):self.read(12)

def pack(f,*v):return struct.pack('<'+f,*v)
def string(s):
    b=s.encode('utf-8');n=len(b);a=bytearray()
    while n>=128:a.append((n&127)|128);n>>=7
    a.append(n);return bytes(a)+b

def stable_hash(s):
    encoded=s.encode('utf-16-le',errors='surrogatepass')
    units=struct.unpack('<'+'H'*(len(encoded)//2),encoded)
    a=b=5381
    for i in range(0,len(units),2):
        if units[i]==0:break
        a=((a*33)^units[i])&0xffffffff
        if i+1>=len(units) or units[i+1]==0:break
        b=((b*33)^units[i+1])&0xffffffff
    n=(a+b*1566083941)&0xffffffff
    return n if n<0x80000000 else n-0x100000000

@dataclass
class Item:
    prefab_hash:int
    x:int
    y:int
    quality:int=1
    stack:int=1
    durability_raw:int=10000
    world_level:int=0
    picked:bool=True
    equipped:bool=False
    variant:int=0
    crafter_id:int=0
    crafter_name:str=''
    custom:list=field(default_factory=list)
    tail:int=0
    has_prefab:bool=True
    origin_index:int|None=field(default=None,repr=False,compare=False)
    _original_flags:int=field(default=0,repr=False,compare=False)
    _raw_fields:dict=field(default_factory=dict,repr=False,compare=False)
    _original_values:dict=field(default_factory=dict,repr=False,compare=False)
    @property
    def cheated(self):
        """Raw low bit. Its game meaning depends on the inventory version."""
        return bool(self.tail&1)
    def to_bytes(self):
        if not (0<=self.quality<=65535 and 0<=self.stack<=65535 and 0<=self.x<=255 and 0<=self.y<=255):raise FormatError('Item values out of range')
        flags=(1 if self.picked else 0)|(2 if self.equipped else 0)|(4 if self.quality!=1 else 0)|(8 if self.stack!=1 else 0)|(16 if self.variant else 0)|(32 if self.crafter_id else 0)|(64 if self.has_prefab else 0)|(128 if self.custom else 0)
        flags |= self._original_flags & 252
        out=pack('iBBBB',self.durability_raw,self.x,self.y,self.world_level,flags)
        if flags&4:out+=self._encoded('quality',self.quality,pack('H',self.quality))
        if flags&8:out+=self._encoded('stack',self.stack,pack('H',self.stack))
        if flags&16:out+=self._encoded('variant',self.variant,pack('i',self.variant))
        if flags&32:out+=self._encoded('crafter',(self.crafter_id,self.crafter_name),pack('q',self.crafter_id)+string(self.crafter_name))
        if flags&64:out+=self._encoded('prefab_hash',self.prefab_hash,pack('i',self.prefab_hash))
        if flags&128:
            n=len(self.custom)
            if n>=32768:raise FormatError('Too much custom data')
            custom=(bytes([n]) if n<128 else bytes([128|(n>>8),n&255]))
            for k,v in self.custom:custom+=string(k)+string(v)
            out+=self._encoded('custom',self.custom,custom)
        return out+bytes([self.tail])

    def _encoded(self,name,value,encoded):
        """Retain original optional-field bytes when their value is unchanged."""
        if name in self._raw_fields and value==self._original_values[name]:
            return self._raw_fields[name]
        return encoded

def read_item(r):
    durability=r.i32();x=r.u8();y=r.u8();world=r.u8();f=r.u8()
    raw_fields={}
    def optional(name,bit,read,default):
        if not f&bit:return default
        start=r.p
        value=read()
        raw_fields[name]=r.b[start:r.p]
        return value
    quality=optional('quality',4,r.u16,1)
    stack=optional('stack',8,r.u16,1)
    variant=optional('variant',16,r.i32,0)
    cid,cn=optional('crafter',32,lambda:(r.i64(),r.string()),(0,''))
    pref=optional('prefab_hash',64,r.i32,0)
    custom=[]
    if f&128:
        start=r.p
        n=r.u8();n=((n&127)<<8)|r.u8() if n&128 else n
        for _ in range(n):custom.append((r.string(),r.string()))
        raw_fields['custom']=r.b[start:r.p]
    tail=r.u8()
    item=Item(pref,x,y,quality,stack,durability,world,bool(f&1),bool(f&2),variant,cid,cn,custom,tail,bool(f&64))
    item._original_flags=f
    item._raw_fields=raw_fields
    item._original_values=copy.deepcopy(dict(quality=quality,stack=stack,variant=variant,crafter=(cid,cn),prefab_hash=pref,custom=custom))
    return item

SKILLS={1:'Swords',2:'Knives',3:'Clubs',4:'Polearms',5:'Spears',6:'Blocking',7:'Axes',8:'Bows',9:'Elemental Magic',10:'Blood Magic',11:'Fists',12:'Pickaxes',13:'Wood Cutting',14:'Crossbows',100:'Jump',101:'Sneak',102:'Run',103:'Swim',104:'Fishing',105:'Cooking',106:'Farming',107:'Crafting',108:'Dodge',110:'Riding'}

def skip_strings(r):
    n=r.i32()
    if not 0<=n<100000:raise FormatError('Invalid list length')
    for _ in range(n):r.string()

def skip_dict(r):
    n=r.i32()
    if not 0<=n<100000:raise FormatError('Invalid dictionary length')
    for _ in range(n):r.string();r.f32()

def skip_world(r):
    r.i64();r.u8();r.vector();r.u8();r.vector();r.u8();r.vector();r.vector()
    if r.u8():r.arr()


def validate_player_34_tail(reader):
    """Check the post-skills structure while preserving its original bytes."""
    for _ in range(reader.count()):
        reader.string()
        reader.string()
    reader.read(12)  # current stamina, maximum eitr, current eitr
    reader.arr()  # opaque build UI payload
    for _ in range(2):  # pseudo-counter table, then upgrade seed table
        reader.read(reader.count() * 8)
    if reader.p != len(reader.b):
        raise FormatError("Unexpected trailing data in player version 34")


def writable_inventory_rows(unique_entries):
    """Use verified v34 pocket state within ULF's existing six-row add limit."""
    values = []
    for entry in unique_entries:
        parts = entry.split(" ", 2)
        if len(parts) >= 2 and parts[0].lower() == "invrows":
            values.append(parts[1].strip())
    if not values:
        return 4
    if len(set(values)) != 1:
        return 0
    value = values[0]
    if not re.fullmatch(r"[+-]?[0-9]{1,10}", value):
        return 0
    rows = int(value)
    if not -(2**31) <= rows < 2**31:
        return 0
    return max(0, min(6, rows))


class Character:
    def __init__(self,raw):
        if len(raw)>256*1024*1024:raise FormatError('The character file exceeds the supported size')
        self.original=raw;r=Reader(raw);body=r.arr();digest=r.arr()
        if hashlib.sha512(body).digest()!=digest or r.p!=len(raw):raise FormatError('Invalid SHA-512 or file framing')
        q=Reader(body);self.profile_version=q.i32()
        if self.profile_version not in (44,46,47):
            raise FormatError(f'Unsupported profile version {self.profile_version}; expected 44, 46 or 47')
        stat_count=q.i32();buckets=q.i32()
        if not 0<=stat_count<5000 or not 0<=buckets<100:raise FormatError('Invalid stats metadata')
        for _ in range(buckets):
            q.read(stat_count*4)
            for j in range(3):skip_dict(q)
            for j in range(q.count()):skip_dict(q)
            for j in range(5):skip_dict(q)
        q.u8()
        for _ in range(q.count()):skip_world(q)
        self.name=q.string();q.i64();q.string();self.used_cheats=bool(q.u8());q.i64()
        if not q.u8():raise FormatError('Character contains no player data')
        pdata_start=q.p;self.player_data=q.arr();pdata_end=q.p
        if q.p!=len(body):raise FormatError('Unexpected profile trailing data')
        self.prefix=body[:pdata_start];self.suffix=body[pdata_end:]
        p=Reader(self.player_data);self.player_version=p.i32()
        current = self.profile_version == 47
        if (current and self.player_version != 34) or (not current and not 23 <= self.player_version <= 33):
            expected = "34" if current else "23–33"
            raise FormatError(f'Unsupported player data version {self.player_version} for profile {self.profile_version}; expected {expected}')
        if self.player_version>=7:p.f32()
        p.f32()
        if self.player_version>=10:p.f32()
        if self.player_version>=20:p.f32()
        if self.player_version>=23:p.string()
        if self.player_version>=24:p.f32()
        self.head=self.player_data[:p.p]
        self.inventory_version=p.i32()
        expected_inventory = 110 if current else 109
        if self.inventory_version != expected_inventory:
            raise FormatError(f'Unsupported inventory version {self.inventory_version} for profile {self.profile_version}; expected {expected_inventory}')
        count=p.u16();self.items=[read_item(p) for _ in range(count)]
        for index,item in enumerate(self.items):item.origin_index=index
        mid_start=p.p
        skip_strings(p)
        for _ in range(p.count()):p.string();p.i32()
        skip_strings(p)  # materials
        skip_strings(p)  # tutorials
        if current:
            self.writable_inventory_rows = writable_inventory_rows(p.string() for _ in range(p.count()))
        else:
            skip_strings(p)  # uniques
            self.writable_inventory_rows = 6
        skip_strings(p)  # trophies
        skip_strings(p) # known biomes
        for _ in range(p.count()):p.string();p.string()
        p.string();p.string();p.vector();p.vector();p.i32()
        for _ in range(p.count()):p.string();p.f32()
        self.middle=self.player_data[mid_start:p.p]
        self.skills_version=p.i32();n=p.i32()
        if self.skills_version!=2 or not 0<=n<500:raise FormatError('Unsupported skills section')
        self.skills=[]
        self._skill_bytes=[]
        for _ in range(n):
            start=p.p
            self.skills.append([p.i32(),p.f32(),p.f32()])
            self._skill_bytes.append(self.player_data[start:p.p])
        self._original_skills=copy.deepcopy(self.skills)
        self.tail=self.player_data[p.p:]
        if current:
            validate_player_34_tail(p)
        self.roundtrip=self.serialize()==raw

    def item_cheat_status(self, item):
        """Return the v110 bit meaning, or None for an opaque legacy byte."""
        return item.cheated if self.inventory_version == 110 else None

    def serialize(self):
        if len(self.items)>65535:raise FormatError('Too many items')
        inv=pack('iH',self.inventory_version,len(self.items))+b''.join(x.to_bytes() for x in self.items)
        if len(self.skills)>=500:raise FormatError('Too many skill records')
        skill_records=[]
        for index,row in enumerate(self.skills):
            if len(row)!=3:raise FormatError('A skill record must contain an ID, level and experience')
            original=self._original_skills[index] if index<len(self._original_skills) else None
            fields=[]
            for column,(kind,value) in enumerate(zip('iff',row)):
                same=original is not None and (value==original[column] or (column>0 and type(value) in (int,float) and math.isnan(value) and math.isnan(original[column])))
                if not same:
                    if column==0 and (type(value) is not int or not -(2**31)<=value<2**31):raise FormatError('Invalid skill identifier')
                    if column>0 and (type(value) not in (int,float) or not math.isfinite(value) or value<0 or (column==1 and value>100) or (column==2 and value>=1e9)):raise FormatError('Invalid modified skill value')
                fields.append(self._skill_bytes[index][column*4:column*4+4] if same else pack(kind,value))
            skill_records.append(b''.join(fields))
        sk=pack('ii',self.skills_version,len(self.skills))+b''.join(skill_records)
        player=self.head+inv+self.middle+sk+self.tail
        body=self.prefix+pack('i',len(player))+player+self.suffix
        return pack('i',len(body))+body+pack('i',64)+hashlib.sha512(body).digest()
    def set_skill(self,id,level):
        from core.editing import apply_skills
        apply_skills(self,[(id,level,None)])
    def add(self,prefab,x,y,quality=1,stack=1):
        if not self.roundtrip:raise FormatError('The original character failed round-trip validation')
        metadata=CATALOG.get(prefab)
        if not metadata or metadata.get('max_stack') is None:raise FormatError('This item has no verified stack limit and cannot be added')
        if type(stack) is not int or not 1<=stack<=min(metadata['max_stack'],65535):raise FormatError('Quantity exceeds the verified item stack limit')
        if type(quality) is not int or not 1<=quality<=65535:raise FormatError('Quality must be between 1 and 65,535')
        if any(t.x==x and t.y==y for t in self.items):raise FormatError('Slot occupied')
        if type(x) is not int or type(y) is not int or not 0<=x<8 or not 0<=y<self.writable_inventory_rows:
            raise FormatError('Slot out of bounds for item creation')
        self.items.append(Item(stable_hash(prefab),x,y,quality,stack))
