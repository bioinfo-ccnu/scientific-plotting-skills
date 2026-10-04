# Heuristic QA of rendered SVG text; reports need visual review.
scientific_contrast <- function(foreground, background) {
  rgb <- grDevices::col2rgb(c(foreground,background))/255
  linear <- ifelse(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)^2.4)
  luminosity <- as.numeric(c(0.2126,0.7152,0.0722) %*% linear)
  (max(luminosity)+0.05)/(min(luminosity)+0.05)
}

inspect_scientific_svg <- function(path, background = "white", minimum_font_size = 6, minimum_text_contrast = 3) {
  if(!requireNamespace("xml2",quietly=TRUE)) stop("Install xml2 for rendered SVG QA")
  document <- xml2::read_xml(path); xml2::xml_ns_strip(document)
  root <- xml2::xml_root(document)
  number <- function(x,default=0) {value<-suppressWarnings(as.numeric(gsub("[^0-9.eE+-]","",x))); if(length(value)!=1 || !is.finite(value)) default else value}
  width <- number(xml2::xml_attr(root,"width")); height <- number(xml2::xml_attr(root,"height"))
  nodes <- xml2::xml_find_all(document,".//text")
  findings <- list(); bounds <- list()
  add <- function(code,...) findings[[length(findings)+1]] <<- c(list(code=code),list(...))
  for(node in nodes) {
    text <- xml2::xml_text(node); if(!nzchar(trimws(text))) next
    style <- xml2::xml_attr(node,"style")
    parts <- strsplit(.sp_or(if(is.na(style)) NULL else style,""),";")[[1]]
    properties <- list()
    for(part in parts) {split<-strsplit(part,":",fixed=TRUE)[[1]]; if(length(split)>=2) properties[[trimws(split[1])]]<-trimws(paste(split[-1],collapse=":"))}
    size <- number(properties[["font-size"]],9)
    family <- gsub("['\"]","",.sp_or(properties[["font-family"]],"sans"))
    family <- trimws(strsplit(family,",",fixed=TRUE)[[1]][1])
    color <- .sp_or(properties$fill,xml2::xml_attr(node,"fill"))
    if(is.null(color)||is.na(color)||color=="none") color<-"#202020"
    x <- number(xml2::xml_attr(node,"x")); y <- number(xml2::xml_attr(node,"y"))
    text_width <- as.numeric(systemfonts::string_width(text,family=family,size=size,res=72))
    anchor <- xml2::xml_attr(node,"text-anchor")
    if(is.na(anchor)) anchor <- .sp_or(properties[["text-anchor"]],"start")
    left <- x-if(anchor=="middle")text_width/2 else if(anchor=="end")text_width else 0
    corners <- rbind(c(left,y-size*0.85),c(left+text_width,y-size*0.85),c(left,y+size*0.2),c(left+text_width,y+size*0.2))
    transform <- xml2::xml_attr(node,"transform")
    if(!is.na(transform)) {
      rotation <- regmatches(transform,regexpr("rotate\\([^)]*\\)",transform))
      if(length(rotation)) {
        angle <- number(rotation)*pi/180
        corners <- corners %*% matrix(c(cos(angle),-sin(angle),sin(angle),cos(angle)),2)
      }
      translation <- regmatches(transform,regexpr("translate\\([^)]*\\)",transform))
      if(length(translation)) {
        xy <- as.numeric(strsplit(gsub("translate\\(|\\)","",translation),"[ ,]+")[[1]])
        if(length(xy)==2) corners <- sweep(corners,2,xy,"+")
      }
    }
    box <- c(min(corners[,1]),min(corners[,2]),max(corners[,1]),max(corners[,2]))
    if(box[1]< -2 || box[2]< -2 || box[3]>width+2 || box[4]>height+2) add("clipped-text",text=text)
    if(size<minimum_font_size) add("small-text",text=text,points=size)
    if(!family %in% c("sans","serif","mono",unique(systemfonts::system_fonts()$family))) add("missing-font",text=text,family=family)
    characters <- strsplit(text,"")[[1]]
    glyphs <- systemfonts::glyph_info(characters,family=family)
    missing <- unique(characters[glyphs$index==0 & !grepl("^[[:space:]]$",characters)])
    if(length(missing)) add("missing-glyph",text=text,characters=missing)
    ratio <- tryCatch(scientific_contrast(color,background),error=function(e) NA_real_)
    if(is.finite(ratio)&&ratio<minimum_text_contrast) add("low-text-contrast",text=text,ratio=ratio)
    bounds[[length(bounds)+1]] <- list(text=text,box=box)
  }
  if(length(bounds)>1) for(i in seq_len(length(bounds)-1)) for(j in (i+1):length(bounds)) {
    a<-bounds[[i]]$box; b<-bounds[[j]]$box
    area<-max(0,min(a[3],b[3])-max(a[1],b[1]))*max(0,min(a[4],b[4])-max(a[2],b[2]))
    if(area>0.15*min((a[3]-a[1])*(a[4]-a[2]),(b[3]-b[1])*(b[4]-b[2]))) add("text-overlap",texts=c(bounds[[i]]$text,bounds[[j]]$text))
  }
  list(backend="ggplot2",status=if(length(findings))"review" else "pass",
       checks=c("rendered-SVG-text-bounds","estimated-text-overlap","fonts-glyphs","font-size","text-contrast"),
       limitations=c("Glyph bounds and transforms are approximate","Does not inspect image-internal text or certify journal compliance"),findings=findings)
}

inspect_scientific_exports <- function(paths,width_mm,height_mm,dpi,minimum_dpi=300) {
  findings<-list(); files<-list()
  if(any(c("png","tiff") %in% names(paths))&&dpi<minimum_dpi) findings[[length(findings)+1]]<-list(code="low-raster-resolution",dpi=dpi)
  for(format in setdiff(names(paths),"manifest")) {
    path<-paths[[format]]; detail<-list(bytes=file.info(path)$size)
    if(format=="png") {
      header<-readBin(path,"raw",n=24); uint32<-function(v)sum(as.integer(v)*256^(3:0))
      size<-c(uint32(header[17:20]),uint32(header[21:24])); detail$pixels<-size
      if(any(abs(size-c(width_mm,height_mm)/25.4*dpi)>1)) findings[[length(findings)+1]]<-list(code="wrong-raster-dimensions",file=path)
    } else if(format=="pdf") {
      detail$page_mm<-.sp_pdf_page_mm(path)
      if(any(abs(unlist(detail$page_mm)-c(width_mm,height_mm))>0.02)) findings[[length(findings)+1]]<-list(code="pdf-page-rounding",page_mm=detail$page_mm)
    }
    files[[format]]<-detail
  }
  list(files=files,findings=findings)
}
