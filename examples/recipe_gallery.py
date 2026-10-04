"""Render category galleries with either backend and an explicit output root."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"skills/scientific-plotting/scripts"))
from plot_cli import run_config

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--backend",choices=["python","r"],default="python")
    parser.add_argument("--out",type=Path,default=ROOT/"build/recipes")
    parser.add_argument("--overwrite",action="store_true")
    args=parser.parse_args()
    for name in ["general","bioinformatics","evaluation","network-single-cell"]:
        run_config(ROOT/f"examples/configs/gallery-{name}.yml",backend=args.backend,
                   output=args.out/f"{args.backend}-{name}",overwrite=args.overwrite)
