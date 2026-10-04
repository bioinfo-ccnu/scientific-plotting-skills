"""Generate clearly synthetic, shared input templates and runnable YAML jobs."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/scientific-plotting"
sys.path.insert(0,str(SKILL / "scripts"))
from plot_recipes import CATALOG

rng = np.random.default_rng(2026)
data_dir = SKILL / "assets/templates"
data_dir.mkdir(exist_ok=True)
config_dir = ROOT / "examples/configs"
config_dir.mkdir(exist_ok=True)
groups = ["A","B","C"]
tables = {}
tables["raincloud"] = pd.DataFrame([(g,rng.normal(i*.4,.18)) for i,g in enumerate(groups) for _ in range(24)],columns=["group","value"])
tables["paired"] = pd.DataFrame([(f"S{s:02}",g,0.2+s*.035+i*.23+rng.normal(0,.08)) for s in range(12) for i,g in enumerate(["A","B"])],columns=["subject","group","value"])
tables["ribbon"] = pd.DataFrame([(g,x,np.sin(x/3)*.2+i*.2+.4,np.sin(x/3)*.2+i*.2+.34,np.sin(x/3)*.2+i*.2+.46) for i,g in enumerate(groups) for x in range(10)],columns=["group","x","mean","lower","upper"])
tables["forest"] = pd.DataFrame([(f"Study {i+1}",effect,effect-.2,effect+.2) for i,effect in enumerate([.1,.3,-.1,.5])],columns=["label","effect","lower","upper"])
base = rng.normal(size=(10,4));base[:,1]=base[:,0]*.7+rng.normal(0,.3,10)
tables["correlation"] = pd.DataFrame([(f"S{s+1}",f"F{f+1}",base[s,f]) for s in range(10) for f in range(4)],columns=["sample","feature","value"])
tables["dendrogram"] = tables["correlation"].iloc[:24].copy()
tables["facet"] = pd.DataFrame([(f"Condition {c+1}",g,x,.5*x+i*.3+rng.normal(0,.15)) for c in range(2) for i,g in enumerate(groups) for x in rng.uniform(0,1,12)],columns=["facet","group","x","y"])
tables["volcano"] = pd.DataFrame({"label":[f"Gene{i+1}" for i in range(100)],"log2fc":rng.normal(0,1.5,100),"q":10**rng.uniform(-5,0,100)})
tables["ma"] = tables["volcano"].assign(mean_expression=10**rng.uniform(0,4,100))
tables["enrichment"] = pd.DataFrame({"term":[f"Pathway {i+1}" for i in range(5)],"ratio":[.2,.35,.15,.4,.25],"count":[8,14,6,16,10],"q":[.001,.005,.02,.0005,.015]})
tables["upset"] = pd.DataFrame([(f"Gene{i}",g) for i in range(18) for j,g in enumerate(groups) if (i+j)%3 != 0 or i%4==0],columns=["item","set"])
tables["heatmap"] = pd.DataFrame([(f"F{r+1}",f"S{c+1}",rng.normal()+c*.2,"A" if r<3 else "B","A" if c<2 else "B") for r in range(6) for c in range(4)],columns=["row","column","value","row_group","column_group"])
truth = np.array([0,1]*30)
classification = pd.DataFrame([(g,f"S{s+1}",int(y),float(np.clip(.2+.55*y+rng.normal(0,.18+i*.07),0,1))) for i,g in enumerate(groups) for s,y in enumerate(truth)],columns=["model","sample","truth","score"])
for kind in ["roc","pr","calibration"]:
    tables[kind] = classification
tables["confusion"] = classification.loc[classification.model=="A",["truth","score"]].assign(prediction=lambda d:(d.score>=.5).astype(int)).drop(columns="score")
observed = rng.uniform(0,1,30)
tables["prediction"] = pd.DataFrame([(g,float(x),float(x+rng.normal(0,.08+i*.035))) for i,g in enumerate(groups) for x in observed],columns=["model","observed","predicted"])
tables["ablation"] = pd.DataFrame([(g,c,.8-i*.04-j*.06) for i,g in enumerate(groups) for j,c in enumerate(["Full","No sequence","No structure"])],columns=["model","component","value"])
tables["benchmark"] = pd.DataFrame([(g,m,value) for g,offset in zip(groups,[0,.05,.1]) for m,value in [("AUROC",.9-offset),("RMSE",.2+offset)]],columns=["model","metric","value"])
tables["network"] = pd.DataFrame({"source":["P1","P1","P2","P3","P4","P5"],"target":["P2","P3","P4","P4","P5","P6"],"weight":[.6,.3,.8,-.2,.5,.7]})
tables["umap"] = pd.DataFrame([(f"Cell{i}-{j}",g,float(rng.normal(i*3,.6)),float(rng.normal((i%2)*2,.5))) for i,g in enumerate(groups) for j in range(25)],columns=["cell","group","umap1","umap2"])
tables["dotplot"] = pd.DataFrame([(g,f"Gene{j+1}",rng.uniform(0,3),rng.uniform(.05,1)) for g in groups for j in range(4)],columns=["group","gene","mean_expression","fraction"])
options = {"ribbon":{"interval_definition":"synthetic supplied ±0.06 interval; not inferred CI"},
           "forest":{"interval_definition":"synthetic supplied interval; not inferred CI"},
           "heatmap":{"center":0,"cluster_rows":True,"cluster_columns":True},
           "prediction":{"inset":{"xlim":[.2,.5],"ylim":[.2,.5]}}, "network":{"layout":"circular"}}
panels = {}
for kind in CATALOG:
    tables[kind].to_csv(data_dir/f"{kind}.csv",index=False)
    panel={"type":kind,"data":f"../../skills/scientific-plotting/assets/templates/{kind}.csv",
           "options":{"title":kind.replace("_"," ").title(),**options.get(kind,{})}}
    panels[kind]=panel
    config={"version":1,"backend":"python","synthetic":True,"preset":"nature","output":f"../../build/recipes/{kind}",
            "width_mm":140,"height_mm":100,"dpi":300,"formats":["pdf","svg","png"],"title":"SYNTHETIC DATA", "panels":[panel]}
    (config_dir/f"{kind}.yml").write_text(yaml.safe_dump(config,sort_keys=False))
for category in sorted({s["category"] for s in CATALOG.values()}):
    selected=[panels[k] for k,v in CATALOG.items() if v["category"]==category]
    config={"version":1,"backend":"python","synthetic":True,"presets":["nature","dark"],"output":f"../../build/recipes/{category}",
            "width_mm":260,"height_mm":220 if len(selected)>4 else 170,"dpi":180,"formats":["pdf","svg","png"],
            "title":f"{category.upper()} | SYNTHETIC DATA","layout":{"ncols":3,"tags":True},"panels":selected}
    (config_dir/f"gallery-{category}.yml").write_text(yaml.safe_dump(config,sort_keys=False))
stat_panel=dict(panels["paired"],statistics={"method":"paired-t","experimental_unit":"independent synthetic subject","contrasts":[["A","B"]],"confidence":.95,"adjust":"bh"})
config={"version":1,"backend":"python","synthetic":True,"presets":["nature","dark"],"output":"../../build/recipes/statistics",
        "width_mm":150,"height_mm":100,"dpi":300,"title":"SYNTHETIC DATA | explicit paired comparison","panels":[stat_panel]}
(config_dir/"statistics.yml").write_text(yaml.safe_dump(config,sort_keys=False))
wide = tables["paired"].pivot(index="subject",columns="group",values="value").reset_index()
with pd.ExcelWriter(data_dir/"paired-wide.xlsx",engine="openpyxl") as writer:
    wide.to_excel(writer,index=False,sheet_name="Measurements")
panel={"type":"paired","data":"../../skills/scientific-plotting/assets/templates/paired-wide.xlsx","sheet":"Measurements",
       "reshape":{"mode":"long","id_columns":["subject"],"value_columns":["A","B"],"names_to":"group","values_to":"value"},
       "statistics":stat_panel["statistics"]}
config=dict(config,panels=[panel],presets=["minimal"],output="../../build/recipes/excel")
(config_dir/"excel.yml").write_text(yaml.safe_dump(config,sort_keys=False))
print(f"Generated {len(CATALOG)} CSV templates, XLSX reshape template, individual and gallery YAML jobs")
