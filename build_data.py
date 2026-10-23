# ============================================================
# สร้างข้อมูลสำหรับเว็บ: สถิติรายตำบล (JSON) + ภาพแผนที่ (PNG, EPSG:3857)
# ============================================================
import pickle, json, numpy as np, geopandas as gpd, rasterio, io, base64, hashlib
from rasterio.warp import reproject, Resampling, calculate_default_transform, transform_bounds
from rasterio.features import rasterize
from PIL import Image
res,comb=pickle.load(open("res.pkl","rb"))
g=gpd.read_file("tambon.geojson")
B="/mnt/user-data/uploads/ZipNew - Copy/"; P="/mnt/user-data/uploads/Project - Copy/"

# --- ค่าฝนเฉลี่ย (มม./ปี) และอุณหภูมิเฉลี่ย (°C) รายตำบล ---
def zmean(path):
    with rasterio.open(path) as r:
        a=r.read(1,masked=True).astype("float64")
        gg=g.to_crs(32647).copy() if r.crs.to_epsg()==32647 else g.to_crs(r.crs)
        z=rasterize(zip(gg.geometry,range(1,len(gg)+1)),out_shape=a.shape,transform=r.transform,fill=0,all_touched=True)
    m=(~a.mask)&(z>0)
    s=np.bincount(z[m],weights=a.data[m],minlength=len(g)+1); c=np.bincount(z[m],minlength=len(g)+1)
    return [round(float(s[i]/c[i]),1) if c[i] else None for i in range(1,len(g)+1)]
rain=zmean(P+"ปริมาณน้ำฝนคาบ10ปี/ปริมาณน้ำฝน10ปี.tif")
temp=zmean(P+"อุณหภูมิเฉลี่ย2015-2025/2015-2025.tif")

FACT=["ph","texture","slope","river","rain","irrig","temp","humid"]
def r0(x): return int(round(float(x)))
T=[]
for i,row in g.iterrows():
    k=i+1
    t={"id":k,"t":row.T_NAME_T,"a":row.A_NAME_T.replace("กิ่งอำเภอ",""),"te":row.T_NAME_E.title(),"km2":round(row.Area_km2,1),
       "rain":rain[i],"temp":temp[i],"c":{}, "comb":[r0(comb[k][v]) for v in [0,1,2,4,5,6,7,11,12,13]]}
    for ck in res:
        f=res[ck]["final"][k]
        d={"fin":[r0(f[v]) for v in [1,2,3,4,11,12,13]],"f":{}}
        for fk in FACT:
            h=res[ck][fk][k]; d["f"][fk]=[r0(h[v]) for v in range(5)]
        t["c"][ck]=d
    T.append(t)
prov={ck:{"fin":[r0(res[ck]["final"][1:,v].sum()) for v in [1,2,3,4,11,12,13]],
          "f":{fk:[r0(res[ck][fk][1:,v].sum()) for v in range(5)] for fk in FACT}} for ck in res}
provcomb=[r0(comb[1:,v].sum()) for v in [0,1,2,4,5,6,7,11,12,13]]

# --- ขอบเขตตำบล (simplify ลดขนาดไฟล์) ---
gs=g.to_crs(32647); gs["geometry"]=gs.geometry.simplify(60); gs=gs.to_crs(4326)
gs["id"]=range(1,len(gs)+1)
gj=json.loads(gs[["id","geometry"]].to_json())
for ft in gj["features"]:
    ft.pop("id",None)
    def rd(c): return [rd(x) for x in c] if isinstance(c[0],list) else [round(c[0],4),round(c[1],4)]
    ft["geometry"]["coordinates"]=rd(ft["geometry"]["coordinates"])
    ft["properties"]={"id":ft["properties"]["id"]}

# --- render raster → PNG ใน EPSG:3857 (Leaflet imageOverlay จะวางได้ตรง) ---
SUIT={1:(200,85,61),2:(233,160,59),3:(156,191,90),4:(47,125,79),11:(120,134,112),12:(160,155,165),13:(74,144,184)}
COMB={0:(214,205,190),1:(176,112,52),2:(240,190,40),4:(118,178,92),5:(54,150,138),6:(170,190,60),7:(108,78,160),11:(120,134,112),12:(160,155,165),13:(74,144,184)}
FAC={0:(205,200,190),1:(200,85,61),2:(233,160,59),3:(156,191,90),4:(47,125,79)}
# mask ขอบเขตจังหวัด (ตัด pixel นอกจังหวัด)
prov_geom=g.to_crs(3857).union_all()
def render(path,cmap,res_m,valid):
    with rasterio.open(path) as r:
        b=transform_bounds(r.crs,3857,*r.bounds)
        pb=prov_geom.bounds
        W=int((pb[2]-pb[0])/res_m); H=int((pb[3]-pb[1])/res_m)
        from rasterio.transform import from_bounds
        tr=from_bounds(*pb,W,H)
        dst=np.full((H,W),65535,np.int64)
        src=r.read(1).astype(np.int64)
        reproject(src,dst,src_transform=r.transform,src_crs=r.crs,dst_transform=tr,dst_crs=3857,resampling=Resampling.mode if res_m>60 else Resampling.nearest,src_nodata=None,dst_nodata=65535)
    inside=rasterize([(prov_geom,1)],out_shape=(H,W),transform=tr,fill=0)
    rgba=np.zeros((H,W,4),np.uint8)
    for v,c in cmap.items():
        m=(dst==v)&(inside==1)&np.isin(dst,valid); rgba[m,:3]=c; rgba[m,3]=255
    im=Image.fromarray(rgba,"RGBA").quantize(colors=16,method=Image.Quantize.FASTOCTREE)
    bio=io.BytesIO(); im.save(bio,"PNG",optimize=True)
    return bio.getvalue()
pb=prov_geom.bounds
from pyproj import Transformer
tf=Transformer.from_crs(3857,4326,always_xy=True)
sw=tf.transform(pb[0],pb[1]); ne=tf.transform(pb[2],pb[3])
bounds=[[sw[1],sw[0]],[ne[1],ne[0]]]
CROPS={"guava":("ฝรั่ง",{"final":"GaueFinal","ph":"PH","texture":"Textu","slope":"SLLF","river":"Distance to Rive","rain":"PIP","irrig":"เขตพื้นที่ชลประทาน","temp":"Temp","humid":"Humidity"}),
 "mango":("มะม่วง",{"final":"MangoFina","ph":"PH","texture":"TexTu","slope":"SLLF","river":"Distance to River","rain":"PIP","irrig":"พื้นที่ชลประทาน","temp":"Tep","humid":"Humidity"}),
 "date":("อินทผลัม",{"final":"Date_PlamFina","ph":"PH","texture":"TexTue","slope":"SLLF","river":"Distance to Rive","rain":"PIP","irrig":"พื้นที่เขตชลประทาน","temp":"Temp","humid":"Humidity"})}
imgs={}; pool={}; refs={}
def add(key,data):
    h=hashlib.md5(data).hexdigest()[:10]
    if h not in pool: pool[h]="data:image/png;base64,"+base64.b64encode(data).decode()
    refs[key]=h
for ck,(fd,L) in CROPS.items():
    add(ck+"/final",render(B+fd+"/"+L["final"]+".tif",SUIT,90,[1,2,3,4,11,12,13]))
    for fk in FACT:
        add(ck+"/"+fk,render(B+fd+"/"+L[fk]+".tif",FAC,180,[0,1,2,3,4]))
    print(ck)
add("comb",render(B+"ศักยภาพในกานปลูกพืฃ/crop combination map.tif",COMB,90,[0,1,2,4,5,6,7,11,12,13]))
out={"bounds":bounds,"tambon":T,"prov":prov,"provcomb":provcomb,"geo":gj,"img":refs,"pool":pool}
s=json.dumps(out,ensure_ascii=False,separators=(",",":"))
open("data.js","w").write("window.KK_DATA="+s+";")
print("data.js MB",len(s.encode())/1e6, "unique imgs",len(pool), {k:len(v)//1000 for k,v in pool.items()})
