# YAML batch runner. Rscript plot_cli.R config.yml [--output stem] [--overwrite]
run_scientific_config <- function(path, output = NULL, overwrite = FALSE) {
  if(!requireNamespace("yaml",quietly=TRUE)) stop("Install yaml")
  if(!requireNamespace("patchwork",quietly=TRUE)) stop("Install patchwork")
  if(!requireNamespace("xml2",quietly=TRUE)) stop("Install xml2 for quality checks")
  # Grid layout measurement must not start an implicit Rplots.pdf device.
  if(grDevices::dev.cur()==1L) {
    grDevices::pdf(file=NULL)
    on.exit(grDevices::dev.off(),add=TRUE)
  }
  config_path<-normalizePath(path,mustWork=TRUE); config<-yaml::read_yaml(config_path)
  if(!is.list(config)||is.null(config$version)||config$version!=1||!length(config$panels)) stop("Configuration needs version: 1 and panels")
  base<-dirname(config_path)
  resolve<-function(value) if(grepl("^(/|[A-Za-z]:)",value))value else file.path(base,value)
  presets<-unlist(.sp_or(config$presets,list(.sp_or(config$preset,"science"))))
  if(!length(presets)||anyDuplicated(presets)) stop("Presets must be nonempty and unique")
  formats<-unlist(.sp_or(config$formats,c("pdf","svg","png")))
  if(!length(formats)||anyDuplicated(formats)||any(!formats %in% c("pdf","svg","png","tiff"))) stop("Invalid export formats")
  stem<-if(is.null(output))resolve(.sp_or(config$output,"figures/figure")) else output
  if(!grepl("^(/|[A-Za-z]:)",stem))stem<-file.path(getwd(),stem)
  has_statistics<-any(vapply(config$panels,function(p)!is.null(p$statistics),logical(1)))
  suffixes<-c(formats,"plot.json","qc.json","config.yml","source.R",if(has_statistics)"statistics.csv")
  targets<-unlist(lapply(presets,function(p)paste0(stem,"-",p,".",suffixes)))
  if(!overwrite&&any(file.exists(targets))) stop("Output exists; choose a fresh stem or --overwrite")
  frames<-list(); sources<-list()
  for(panel in config$panels) {
    if(is.null(.recipe_catalog[[panel$type]])||is.null(panel$data)) stop("Panel needs supported type and data")
    if(!is.null(panel$statistics)&&!panel$type %in% c("raincloud","paired")) stop("Statistics brackets support raincloud and paired")
    input<-normalizePath(resolve(panel$data),mustWork=TRUE)
    sheet<-.sp_or(panel$sheet,0); if(is.numeric(sheet))sheet<-sheet+1
    frames[[length(frames)+1]]<-load_scientific_table(input,columns=panel$columns,sheet=sheet,reshape=panel$reshape)
    sources[[length(sources)+1]]<-list(path=input,md5=unname(tools::md5sum(input)))
  }
  width<-.sp_positive(.sp_or(config$width_mm,180),"width_mm"); height<-.sp_positive(.sp_or(config$height_mm,120),"height_mm"); dpi<-.sp_positive(.sp_or(config$dpi,300),"dpi")
  layout<-.sp_or(config$layout,list()); ncols<-.sp_or(layout$ncols,min(2,length(frames)))
  if(!is.numeric(ncols)||ncols<1||ncols!=as.integer(ncols)) stop("layout.ncols must be a positive integer")
  levels<-unlist(config$category_levels)
  if(is.null(levels)) levels<-unique(unlist(lapply(frames,function(d) if("model" %in% names(d))as.character(d$model) else if("group" %in% names(d))as.character(d$group) else character())))
  dir.create(dirname(stem),recursive=TRUE,showWarnings=FALSE)
  stage<-tempfile(".batch-",tmpdir=dirname(stem));dir.create(stage);on.exit(unlink(stage,recursive=TRUE),add=TRUE)
  staged<-character();results<-list()
  shared_limit<-function(axis) {
    ranges<-lapply(seq_along(frames),function(i) {
      kind<-config$panels[[i]]$type;data<-frames[[i]]
      fields<-if(axis=="x")switch(kind,ribbon="x",facet="x",prediction="observed",umap="umap1",NULL) else
        switch(kind,ribbon=c("lower","upper"),facet="y",prediction="predicted",umap="umap2",raincloud="value",paired="value",NULL)
      if(is.null(fields))stop("Shared ",axis," limits unsupported for ",kind,"; use explicit per-panel limits")
      limits<-range(unlist(data[fields]))
      comparison<-config$panels[[i]]$statistics
      if(axis=="y"&&!is.null(comparison)) {
        step<-max(diff(range(data$value)),1e-6)*0.16
        limits[2]<-max(limits[2],max(data$value)+(length(comparison$contrasts)+0.5)*step)
      }
      limits
    })
    range(unlist(ranges))
  }
  xlim<-if(.sp_or(layout$sharex,FALSE))shared_limit("x") else NULL
  ylim<-if(.sp_or(layout$sharey,FALSE))shared_limit("y") else NULL
  for(preset in presets) {
    colors<-if(length(levels))scientific_colors(levels,preset) else NULL
    plots<-list();reports<-list();statistics<-list();render_warnings<-character()
    for(i in seq_along(frames)) {
      panel<-config$panels[[i]];data<-frames[[i]];options<-.sp_or(panel$options,list())
      column<-if("model" %in% names(data))"model" else if("group" %in% names(data))"group" else NULL
      if(!is.null(column)) {
        local_levels<-levels[levels %in% as.character(data[[column]])]; options$levels<-as.list(local_levels); options$colors<-as.list(colors)
      }
      if(!is.null(xlim))options$xlim<-xlim
      if(!is.null(ylim))options$ylim<-ylim
      panel_title<-options$title; options$title<-NULL
      recipe<-draw_scientific_recipe(panel$type,data,preset,options)
      if(!is.null(panel$statistics)) {
        table<-do.call(compare_scientific_groups,c(list(data=data),panel$statistics))
        recipe$plot<-annotate_scientific_comparisons(recipe$plot,table,local_levels,data)
        table$panel<-i;statistics[[length(statistics)+1]]<-table
      }
      # Nested layouts should receive one top-level panel tag, not a tag per strip.
      if(inherits(recipe$plot,"patchwork")) recipe$plot<-patchwork::wrap_elements(panel=patchwork::patchworkGrob(recipe$plot)) + scientific_theme(preset)
      if(!is.null(panel_title)) recipe$plot<-recipe$plot + ggplot2::labs(title=panel_title)
      plots[[i]]<-recipe$plot;reports[[i]]<-recipe$report
    }
    axes_collect<-if(!is.null(xlim)&&!is.null(ylim))"collect" else if(!is.null(xlim))"collect_x" else if(!is.null(ylim))"collect_y" else "keep"
    plot<-patchwork::wrap_plots(plots,ncol=ncols,guides=if(.sp_or(layout$shared_legend,FALSE))"collect" else "keep",axes=axes_collect)
    labels<-unlist(layout$labels)
    if(!is.null(labels)&&length(labels)!=length(plots))stop("Panel label count must match")
    plot<-plot + patchwork::plot_annotation(title=config$title,tag_levels=if(.sp_or(layout$tags,TRUE))if(is.null(labels))"A" else list(labels) else NULL,theme=scientific_theme(preset))
    stage_stem<-file.path(stage,paste0(basename(stem),"-",preset))
    metadata<-list(preset=preset,synthetic=.sp_or(config$synthetic,FALSE),sources=sources,category_colors=as.list(colors),recipes=reports,
                   statistics=lapply(statistics,function(x)split(x,seq_len(nrow(x)))),config_md5=unname(tools::md5sum(config_path)))
    # Always render an SVG in staging for geometry/font checks, even for PDF-only requests.
    all_formats<-unique(c(formats,"svg"))
    paths<-withCallingHandlers(export_scientific(plot,stage_stem,formats=all_formats,width_mm=width,height_mm=height,dpi=dpi,metadata=metadata),
      warning=function(w){render_warnings<<-c(render_warnings,conditionMessage(w));invokeRestart("muffleWarning")})
    report<-do.call(inspect_scientific_svg,c(list(path=paths[["svg"]],background=scientific_preset(preset)$background),.sp_or(config$quality,list())))
    if(length(render_warnings)) {
      report$findings<-c(report$findings,lapply(unique(render_warnings),function(w)list(code="render-warning",detail=w)));report$status<-"review"
    }
    if(!"svg" %in% formats) {
      unlink(paths[["svg"]]);paths<-paths[names(paths)!="svg"]
      manifest<-jsonlite::fromJSON(paths[["manifest"]],simplifyVector=FALSE);manifest$formats<-as.list(formats)
      writeLines(jsonlite::toJSON(manifest,auto_unbox=TRUE,pretty=TRUE,null="null",digits=10),paths[["manifest"]])
    }
    report$exports<-inspect_scientific_exports(paths,width,height,dpi)
    if(length(report$exports$findings)) report$status<-"review"
    writeLines(jsonlite::toJSON(report,auto_unbox=TRUE,pretty=TRUE,null="null",digits=10),paste0(stage_stem,".qc.json"))
    delivered<-config;delivered$backend<-"r";delivered$output<-stem
    for(i in seq_along(delivered$panels))delivered$panels[[i]]$data<-sources[[i]]$path
    yaml::write_yaml(delivered,paste0(stage_stem,".config.yml"))
    source_lines<-c("# Usage: Rscript SOURCE.R /path/to/skill/scripts", "args <- commandArgs(trailingOnly=TRUE)","if(length(args)!=1)stop('Supply installed skill scripts directory')", "source(file.path(args[[1]], 'plot_cli.R'))", "script <- sub('^--file=', '', commandArgs()[grepl('^--file=', commandArgs())][1])", "run_scientific_config(sub('\\\\.source\\\\.R$', '.config.yml', normalizePath(script)), overwrite=TRUE)")
    writeLines(source_lines,paste0(stage_stem,".source.R"))
    if(length(statistics))write.csv(do.call(rbind,statistics),paste0(stage_stem,".statistics.csv"),row.names=FALSE)
    staged<-c(staged,paste0(stage_stem,".",suffixes))
    results[[preset]]<-list(stem=paste0(stem,"-",preset),quality=report$status,metrics=reports)
  }
  if(!all(file.exists(staged)))stop("Missing staged output; no batch published")
  for(i in seq_along(targets)) {
    if(!overwrite&&file.exists(targets[i]))stop("Output appeared during batch")
    if(!file.rename(staged[i],targets[i]))stop("Could not publish ",targets[i])
  }
  results
}

.cli_source<-if(sys.nframe()>0)sys.frame(1)$ofile else NULL
if(is.null(.cli_source)) {
  script<-sub("^--file=","",commandArgs()[grepl("^--file=",commandArgs())][1]);.cli_source<-script
}
.cli_dir<-dirname(normalizePath(.cli_source))
for(file in c("scientific_style.R","plot_data.R","plot_statistics.R","plot_recipes.R","figure_tools.R"))source(file.path(.cli_dir,file))
if(sys.nframe()==0) {
  args<-commandArgs(trailingOnly=TRUE)
  if(!length(args))stop("Usage: Rscript plot_cli.R config.yml [--output stem] [--overwrite]")
  output<-if("--output" %in% args)args[match("--output",args)+1] else NULL
  result<-run_scientific_config(args[1],output=output,overwrite="--overwrite" %in% args)
  cat(jsonlite::toJSON(result,auto_unbox=TRUE,null="null"),"\n")
}
