# ============================================================
# Zonal statistics รายตำบล สำหรับเว็บแสดงผลความเหมาะสมพืช 3 ชนิด จ.ขอนแก่น
# Method: rasterize ขอบเขตตำบลลงบน grid ของแต่ละ raster แล้วนับ pixel ต่อ class
# หมายเหตุ: shapefile .prj ระบุ WGS84 แต่พิกัดจริงเป็น UTM 47N → กำหนด CRS ใหม่
# ============================================================
import rasterio, numpy as np, geopandas as gpd, json
from rasterio.features import rasterize
B="/mnt/user-data/uploads/ZipNew - Copy/"
g=gpd.read_file("/mnt/user-data/uploads/Project - Copy/Khonkeant.shp").set_crs(32647,allow_override=True)
g["tid"]=np.arange(1,len(g)+1)
N=len(g)+1
CROPS={
 "guava":("ฝรั่ง",{"final":"GaueFinal","ph":"PH","texture":"Textu","slope":"SLLF","river":"Distance to Rive","rain":"PIP","irrig":"เขตพื้นที่ชลประทาน","temp":"Temp","humid":"Humidity"}),
 "mango":("มะม่วง",{"final":"MangoFina","ph":"PH","texture":"TexTu","slope":"SLLF","river":"Distance to River","rain":"PIP","irrig":"พื้นที่ชลประทาน","temp":"Tep","humid":"Humidity"}),
 "date":("อินทผลัม",{"final":"Date_PlamFina","ph":"PH","texture":"TexTue","slope":"SLLF","river":"Distance to Rive","rain":"PIP","irrig":"พื้นที่เขตชลประทาน","temp":"Temp","humid":"Humidity"}),
}
def hist(path, valid):
    # นับ pixel ต่อ (ตำบล, class) — valid = ชุด class ที่ถือว่าเป็นข้อมูล
    with rasterio.open(path) as r:
        a=r.read(1).astype(np.int64)
        gg=g.to_crs(r.crs)
        z=rasterize(zip(gg.geometry,gg.tid),out_shape=a.shape,transform=r.transform,fill=0,dtype="int32")
        px=abs(r.res[0]*r.res[1])/1600.0   # 1 ไร่ = 1600 ตร.ม.
    m=np.isin(a,valid)&(z>0)
    K=max(valid)+1
    h=np.bincount(z[m]*K+a[m],minlength=N*K).reshape(N,K)*px
    return h  # หน่วย: ไร่
out={"tambon":[], "province":{}}
res={}
for ck,(folder,L) in CROPS.items():
    res[ck]={}
    res[ck]["final"]=hist(B+folder+"/"+L["final"]+".tif",[1,2,3,4,11,12,13])
    for f,nm in L.items():
        if f=="final": continue
        res[ck][f]=hist(B+folder+"/"+nm+".tif",[0,1,2,3,4])
    print(ck,"done")
comb=hist(B+"ศักยภาพในกานปลูกพืฃ/crop combination map.tif",[0,1,2,3,4,5,6,7,11,12,13])
np.save("/home/claude/work/comb.npy",comb)
import pickle; pickle.dump((res,comb),open("/home/claude/work/res.pkl","wb"))
g.to_crs(4326).to_file("/home/claude/work/tambon.geojson",driver="GeoJSON")
