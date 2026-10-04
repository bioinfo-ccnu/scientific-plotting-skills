# Optional domain libraries. Load plot_cli.R before this file.
.sp_load_domain <- function(packages) {
  for(package in packages) tryCatch(loadNamespace(package),error=function(error)
    stop("Unable to load ",package,": ",conditionMessage(error),call.=FALSE))
  invisible(NULL)
}
ggraph_scientific_network <- function(data, preset="science", layout="fr", directed=FALSE, seed=2026) {
  .sp_load_domain(c("igraph","ggraph"))
  require_scientific_columns(data,c("source","target"));require_scientific_unique(data,c("source","target"))
  if(!directed && anyDuplicated(vapply(seq_len(nrow(data)),function(i)jsonlite::toJSON(sort(c(as.character(data$source[i]),as.character(data$target[i])))),character(1))))stop("Duplicate undirected edges")
  graph<-igraph::graph_from_data_frame(data[,c("source","target"),drop=FALSE],directed=directed)
  had_seed<-exists(".Random.seed",envir=.GlobalEnv,inherits=FALSE)
  if(had_seed)old_seed<-get(".Random.seed",envir=.GlobalEnv)
  on.exit(if(had_seed)assign(".Random.seed",old_seed,envir=.GlobalEnv) else if(exists(".Random.seed",envir=.GlobalEnv,inherits=FALSE))rm(".Random.seed",envir=.GlobalEnv),add=TRUE)
  set.seed(seed)
  ggraph::ggraph(graph,layout=layout) + ggraph::geom_edge_link(colour="gray",linewidth=0.4,
    arrow=if(directed)grid::arrow(length=grid::unit(1.5,"mm")) else NULL) +
    ggraph::geom_node_point(colour="#56B4E9",size=3) + ggraph::geom_node_text(ggplot2::aes(label=name),repel=TRUE,size=2.5,colour=scientific_preset(preset)$foreground) + scientific_theme(preset)
}

complex_scientific_heatmap <- function(data,preset="science",cluster_rows=TRUE,cluster_columns=TRUE,
                                       linkage="average",distance="euclidean",center=NULL) {
  .sp_load_domain("ComplexHeatmap")
  if(grDevices::dev.cur()==1L) {
    grDevices::pdf(file=NULL)
    on.exit(grDevices::dev.off(),add=TRUE)
  }
  require_scientific_columns(data,c("row","column","value"),"value")
  matrix<-scientific_matrix(data,"row","column","value")
  if(linkage=="ward") {if(distance!="euclidean")stop("Ward requires Euclidean distance");linkage<-"ward.D2"}
  row_annotation<-NULL;column_annotation<-NULL
  annotation_fields<-intersect(c("row_group","column_group"),names(data))
  annotation_colors<-scientific_colors(sort(unique(as.character(unlist(data[annotation_fields])))),preset)
  for(field in c("row_group","column_group")) {
    if(!field %in% names(data))next
    key<-if(field=="row_group")"row" else "column"
    require_scientific_columns(data,field)
    annotation<-unique(data[c(key,field)]);require_scientific_unique(annotation,key)
    order<-if(key=="row")rownames(matrix) else colnames(matrix)
    groups<-as.character(annotation[[field]][match(order,annotation[[key]])])
    colors<-annotation_colors
    if(key=="row")row_annotation<-ComplexHeatmap::rowAnnotation(Row_group=groups,col=list(Row_group=colors)) else
      column_annotation<-ComplexHeatmap::HeatmapAnnotation(Column_group=groups,col=list(Column_group=colors))
  }
  color<-NULL
  if(!is.null(center)) {
    span<-max(abs(matrix-center));if(span==0)stop("Centered heatmap needs a range")
    color<-circlize::colorRamp2(center+c(-span,0,span),c("#2166AC","white","#B2182B"))
  }
  config<-scientific_preset(preset)
  arguments<-list(matrix=matrix,name="Value",cluster_rows=cluster_rows,cluster_columns=cluster_columns,
    clustering_method_rows=linkage,clustering_method_columns=linkage,clustering_distance_rows=distance,clustering_distance_columns=distance,
    left_annotation=row_annotation,top_annotation=column_annotation,row_names_gp=grid::gpar(fontsize=config$font_size),column_names_gp=grid::gpar(fontsize=config$font_size))
  if(!is.null(color))arguments$col<-color
  heatmap<-do.call(ComplexHeatmap::Heatmap,arguments)
  grid::grid.grabExpr(ComplexHeatmap::draw(heatmap))
}
