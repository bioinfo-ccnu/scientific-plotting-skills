# Optional integration demonstrations with supplied synthetic data.
script <- sub("^--file=", "", commandArgs()[grepl("^--file=", commandArgs())][1])
root <- dirname(dirname(normalizePath(script)))
source(file.path(root,"skills/scientific-plotting/scripts/plot_cli.R"))
source(file.path(root,"skills/scientific-plotting/scripts/specialized_adapters.R"))
args <- commandArgs(trailingOnly=TRUE)
out <- if(length(args)) args[1] else file.path(root,"build/domain-r")
overwrite <- "--overwrite" %in% args
template <- function(name) load_scientific_table(file.path(root,"skills/scientific-plotting/assets/templates",paste0(name,".csv")))
network <- ggraph_scientific_network(template("network"),preset="nature",layout="fr",seed=2026) +
  ggplot2::labs(title="SYNTHETIC DATA | ggraph network")
export_scientific(network,file.path(out,"ggraph-network"),width_mm=160,height_mm=120,
                  metadata=list(synthetic=TRUE,seed=2026),overwrite=overwrite)
heatmap <- complex_scientific_heatmap(template("heatmap"),preset="nature",center=0)
heatmap$vp <- grid::viewport(y=0.46,height=0.88)
heatmap <- grid::grobTree(heatmap,grid::textGrob("SYNTHETIC DATA | ComplexHeatmap",y=0.98,gp=grid::gpar(fontsize=9)))
export_scientific(heatmap,file.path(out,"complex-heatmap"),width_mm=160,height_mm=120,
                  metadata=list(synthetic=TRUE,description="Supplied synthetic matrix; not a research result"),overwrite=overwrite)
