import json
from pathlib import Path
import sys
import subprocess
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"skills/scientific-plotting/scripts"
sys.path.insert(0,str(SCRIPTS))
from plot_recipes import CATALOG,draw_recipe,classification_metrics,intersection_counts
from plot_data import load_table,reshape_table
from plot_statistics import compare_groups,adjust_pvalues
from figure_tools import figure_quality,contrast_ratio
from plot_cli import run_config
from scientific_style import figure_style,export_figure


@pytest.mark.parametrize("kind",CATALOG)
def test_every_recipe_renders_supplied_template(kind,tmp_path):
    config=yaml.safe_load((ROOT/f"examples/configs/{kind}.yml").read_text())
    panel=config["panels"][0]
    data=load_table(ROOT/"examples/configs"/panel["data"])
    with figure_style("nature",overrides={"figure.figsize":(6,4)}):
        fig,ax=plt.subplots(layout="constrained")
        result=draw_recipe(kind,data,ax,options=panel.get("options"))
        paths=export_figure(fig,tmp_path/kind,formats=("png",),dpi=90)
        plt.close(fig)
    assert result["n_rows"]==len(data)
    assert paths["png"].stat().st_size>1000


def test_metrics_use_predictions_and_handle_ties():
    data=pd.DataFrame({"truth":[0,0,1,1],"score":[.1,.4,.35,.8]})
    result=classification_metrics(data)
    assert result["auroc"]==pytest.approx(.75)
    assert result["average_precision"]==pytest.approx(5/6)
    assert result["brier"]==pytest.approx(np.mean((data.truth-data.score)**2))
    tied=classification_metrics(data.assign(score=.5))
    assert tied["auroc"]==.5 and tied["average_precision"]==.5
    with pytest.raises(ValueError): classification_metrics(data.assign(truth=1))
    with pytest.raises(ValueError): classification_metrics(data.assign(score=1.2))


def test_upset_counts_items_not_memberships():
    data=pd.DataFrame({"item":["x","x","y","z"],"set":["A","B","A","B"]})
    counts=intersection_counts(data)
    assert counts.sum()==3 and counts[("A","B")]==1
    with pytest.raises(ValueError): intersection_counts(pd.concat([data,data.iloc[[0]]]))


def test_paired_matching_effects_and_intervals():
    frame=pd.read_csv(ROOT/"skills/scientific-plotting/assets/templates/paired.csv")
    kwargs=dict(contrasts=[["A","B"]],method="paired-t",experimental_unit="subject")
    result=compare_groups(frame,**kwargs).iloc[0]
    shuffled=compare_groups(frame.sample(frac=1,random_state=1),**kwargs).iloc[0]
    a=frame[frame.group=="A"].set_index("subject").value
    b=frame[frame.group=="B"].set_index("subject").value
    assert result.effect==pytest.approx((b-a).mean())
    assert result.effect==shuffled.effect
    assert result.ci_low<result.effect<result.ci_high
    assert result.n_first==12 and result.n_second==12
    with pytest.raises(ValueError): compare_groups(frame.iloc[:-1],**kwargs)
    with pytest.raises(ValueError): compare_groups(pd.concat([frame,frame.iloc[[0]]]),**kwargs)
    with pytest.raises(ValueError): compare_groups(frame,**dict(kwargs,method="welch-t"))
    with pytest.raises(ValueError): compare_groups(frame,**dict(kwargs,experimental_unit=""))


def test_multiplicity_and_nonparametric_seed():
    assert adjust_pvalues([.01,.04,.03]).tolist()==pytest.approx([.03,.04,.04])
    assert adjust_pvalues([.01,.04,.03],"bonferroni").tolist()==pytest.approx([.03,.12,.09])
    frame=pd.read_csv(ROOT/"skills/scientific-plotting/assets/templates/paired.csv")
    kwargs=dict(contrasts=[["A","B"]],method="wilcoxon",experimental_unit="subject",seed=12,bootstrap_samples=200)
    assert compare_groups(frame,**kwargs).equals(compare_groups(frame,**kwargs))


def test_excel_mapping_and_reshape(tmp_path):
    original=pd.DataFrame({"ID":["s1","s2"],"Before":[1,2],"After":[3,4]})
    path=tmp_path/"input.xlsx";original.to_excel(path,index=False)
    data=load_table(path,columns={"subject":"ID","A":"Before","B":"After"},
                    reshape=dict(mode="long",id_columns=["subject"],value_columns=["A","B"],names_to="group",values_to="value"))
    assert len(data)==4 and data.value.sum()==10
    wide=reshape_table(data,mode="wide",index=["subject"],columns="group",values="value")
    assert wide.A.tolist()==[1,2] and wide.B.tolist()==[3,4]
    with pytest.raises(ValueError): reshape_table(pd.concat([data,data.iloc[[0]]]),mode="wide",index=["subject"],columns="group",values="value")


def test_quality_flags_real_geometry_and_contrast():
    with figure_style("nature"):
        fig,ax=plt.subplots()
        fig.text(.5,.5,"Overlap");fig.text(.5,.5,"Overlap")
        fig.text(1.1,.5,"Outside")
        fig.text(.2,.3,"Yellow",color="yellow")
        report=figure_quality(fig)
        plt.close(fig)
    codes={f["code"] for f in report["findings"]}
    assert {"text-overlap","clipped-text","low-text-contrast"}<=codes
    assert contrast_ratio("black","white")==pytest.approx(21)


def _config(tmp_path,presets=None):
    config=yaml.safe_load((ROOT/"examples/configs/statistics.yml").read_text())
    config["presets"]=presets or ["nature"]
    config["formats"]=["png","svg"]
    config["panels"][0]["data"]=str(ROOT/"skills/scientific-plotting/assets/templates/paired.csv")
    config["output"]=str(tmp_path/"result")
    path=tmp_path/"job.yml";path.write_text(yaml.safe_dump(config))
    return path


def test_batch_outputs_config_source_statistics_and_collision(tmp_path):
    path=_config(tmp_path)
    result=run_config(path)
    assert len(result)==1
    assert (tmp_path/"result-nature.source.py").exists()
    assert len(pd.read_csv(tmp_path/"result-nature.statistics.csv"))==1
    manifest=json.loads((tmp_path/"result-nature.plot.json").read_text())
    assert manifest["metadata"]["sources"][0]["sha256"]
    assert manifest["metadata"]["statistics"][0][0]["n_first"]==12
    with pytest.raises(FileExistsError):run_config(path)
    assert yaml.safe_load((tmp_path/"result-nature.config.yml").read_text())["backend"]=="python"
    subprocess.run([sys.executable,str(tmp_path/"result-nature.source.py"),str(ROOT/"skills/scientific-plotting/scripts")],check=True)
    reproduced=json.loads((tmp_path/"result-nature.plot.json").read_text())
    assert reproduced["metadata"]["statistics"]==manifest["metadata"]["statistics"]


def test_failed_style_batch_does_not_publish_first_style(tmp_path):
    with pytest.raises(ValueError):run_config(_config(tmp_path,["nature","unknown"]))
    assert not list(tmp_path.glob("result*"))


def test_recipe_validation_prevents_silent_data_changes():
    fig,ax=plt.subplots()
    with pytest.raises(ValueError):draw_recipe("volcano",pd.DataFrame({"label":["g"],"log2fc":[1],"q":[0]}),ax)
    with pytest.raises(ValueError):draw_recipe("ribbon",pd.DataFrame({"group":["A"],"x":[1],"mean":[1],"lower":[0],"upper":[2]}),ax)
    with pytest.raises(ValueError):draw_recipe("heatmap",pd.DataFrame({"row":["a","b"],"column":["x","y"],"value":[1,2]}),ax)
    with pytest.raises(ValueError):draw_recipe("umap",pd.DataFrame({"cell":["x","x"],"group":["A","A"],"umap1":[1,2],"umap2":[2,3]}),ax)
    plt.close(fig)


def test_optional_scanpy_existing_embedding(tmp_path):
    pytest.importorskip("scanpy")
    import anndata as ad
    from specialized_adapters import scanpy_umap
    data=ad.AnnData(np.ones((6,2)),obs=pd.DataFrame({"group":pd.Categorical(["A","B"]*3)},index=[str(i) for i in range(6)]))
    with pytest.raises(ValueError):scanpy_umap(data,color="group")
    data.obsm["X_umap"]=np.arange(12,dtype=float).reshape(6,2)
    fig,ax=plt.subplots()
    scanpy_umap(data,color="group",ax=ax,palette={"A":"#0072B2","B":"#D55E00"})
    fig.savefig(tmp_path/"scanpy.png");plt.close(fig)
    assert (tmp_path/"scanpy.png").stat().st_size>1000
