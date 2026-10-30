"""ULF FCH binary engine. Supports Valheim profile 46, player data 33, inventory 109.
Rebuilds inventory and skills only, preserving other profile/player sections byte-for-byte.
"""
import hashlib
import struct
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
    def string(self):return self.read(self.var()).decode('utf-8')
    def arr(self):return self.read(self.i32())
    def vector(self):self.read(12)

def pack(f,*v):return struct.pack('<'+f,*v)
def string(s):
    b=s.encode('utf-8');n=len(b);a=bytearray()
    while n>=128:a.append((n&127)|128);n>>=7
    a.append(n);return bytes(a)+b

def stable_hash(s):
    a=b=5381
    for i in range(0,len(s),2):
        a=((a*33)^ord(s[i]))&0xffffffff
        if i+1<len(s):b=((b*33)^ord(s[i+1]))&0xffffffff
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
    @property
    def cheated(self):return bool(self.tail&1)
    def to_bytes(self):
        if not (1<=self.quality<=65535 and 1<=self.stack<=65535 and 0<=self.x<=255 and 0<=self.y<=255):raise FormatError('Item values out of range')
        flags=(1 if self.picked else 0)|(2 if self.equipped else 0)|(4 if self.quality!=1 else 0)|(8 if self.stack!=1 else 0)|(16 if self.variant else 0)|(32 if self.crafter_id else 0)|(64 if self.has_prefab else 0)|(128 if self.custom else 0)
        out=pack('iBBBB',self.durability_raw,self.x,self.y,self.world_level,flags)
        if flags&4:out+=pack('H',self.quality)
        if flags&8:out+=pack('H',self.stack)
        if flags&16:out+=pack('i',self.variant)
        if flags&32:out+=pack('q',self.crafter_id)+string(self.crafter_name)
        if flags&64:out+=pack('i',self.prefab_hash)
        if flags&128:
            n=len(self.custom)
            if n>=32768:raise FormatError('Too much custom data')
            out+=(bytes([n]) if n<128 else bytes([128|(n>>8),n&255]))
            for k,v in self.custom:out+=string(k)+string(v)
        return out+bytes([self.tail])

def read_item(r):
    durability=r.i32();x=r.u8();y=r.u8();world=r.u8();f=r.u8()
    quality=r.u16() if f&4 else 1;stack=r.u16() if f&8 else 1
    variant=r.i32() if f&16 else 0
    cid=r.i64() if f&32 else 0;cn=r.string() if f&32 else ''
    pref=r.i32() if f&64 else 0
    custom=[]
    if f&128:
        n=r.u8();n=((n&127)<<8)|r.u8() if n&128 else n
        for _ in range(n):custom.append((r.string(),r.string()))
    tail=r.u8()
    return Item(pref,x,y,quality,stack,durability,world,bool(f&1),bool(f&2),variant,cid,cn,custom,tail,bool(f&64))

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

class Character:
    def __init__(self,raw):
        self.original=raw;r=Reader(raw);body=r.arr();digest=r.arr()
        if hashlib.sha512(body).digest()!=digest or r.p!=len(raw):raise FormatError('Invalid SHA-512 or file framing')
        q=Reader(body);self.profile_version=q.i32()
        if self.profile_version not in (44,46):raise FormatError(f'Unsupported profile version {self.profile_version}; expected 44 or 46')
        stat_count=q.i32();buckets=q.i32()
        if not 0<=stat_count<5000 or not 0<=buckets<100:raise FormatError('Invalid stats metadata')
        for _ in range(buckets):
            q.read(stat_count*4)
            for j in range(3):skip_dict(q)
            for j in range(q.i32()):skip_dict(q)
            for j in range(5):skip_dict(q)
        q.u8()
        for _ in range(q.i32()):skip_world(q)
        self.name=q.string();q.i64();q.string();self.used_cheats=bool(q.u8());q.i64()
        if not q.u8():raise FormatError('Character contains no player data')
        pdata_start=q.p;self.player_data=q.arr();pdata_end=q.p
        if q.p!=len(body):raise FormatError('Unexpected profile trailing data')
        self.prefix=body[:pdata_start];self.suffix=body[pdata_end:]
        p=Reader(self.player_data);self.player_version=p.i32()
        if not 23<=self.player_version<=33:raise FormatError(f'Unsupported player data version {self.player_version}')
        if self.player_version>=7:p.f32()
        p.f32()
        if self.player_version>=10:p.f32()
        if self.player_version>=20:p.f32()
        if self.player_version>=23:p.string()
        if self.player_version>=24:p.f32()
        self.head=self.player_data[:p.p]
        self.inventory_version=p.i32()
        if self.inventory_version!=109:raise FormatError(f'Unsupported inventory version {self.inventory_version}')
        count=p.u16();self.items=[read_item(p) for _ in range(count)]
        mid_start=p.p
        skip_strings(p)
        for _ in range(p.i32()):p.string();p.i32()
        for _ in range(4):skip_strings(p) # materials, tutorials, uniques, trophies
        skip_strings(p) # known biomes
        for _ in range(p.i32()):p.string();p.string()
        p.string();p.string();p.vector();p.vector();p.i32()
        for _ in range(p.i32()):p.string();p.f32()
        self.middle=self.player_data[mid_start:p.p]
        self.skills_version=p.i32();n=p.i32()
        if self.skills_version<2 or not 0<=n<500:raise FormatError('Unsupported skills section')
        self.skills=[]
        for _ in range(n):self.skills.append([p.i32(),p.f32(),p.f32()])
        self.tail=self.player_data[p.p:]
        self.roundtrip=self.serialize()==raw
    def serialize(self):
        if len(self.items)>65535:raise FormatError('Too many items')
        inv=pack('iH',self.inventory_version,len(self.items))+b''.join(x.to_bytes() for x in self.items)
        sk=pack('ii',self.skills_version,len(self.skills))+b''.join(pack('iff',*x) for x in self.skills)
        player=self.head+inv+self.middle+sk+self.tail
        body=self.prefix+pack('i',len(player))+player+self.suffix
        return pack('i',len(body))+body+pack('i',64)+hashlib.sha512(body).digest()
    def set_skill(self,id,level):
        if not 0<=level<=100:raise FormatError('Skill must be in [0,100]')
        for row in self.skills:
            if row[0]==id:row[1]=float(level);row[2]=0;return
        self.skills.append([id,float(level),0.0])
    def add(self,prefab,x,y,quality=1,stack=1):
        if any(t.x==x and t.y==y for t in self.items):raise FormatError('Slot occupied')
        if not 0<=x<8 or not 0<=y<6:raise FormatError('Slot out of bounds')
        self.items.append(Item(stable_hash(prefab),x,y,quality,stack))
