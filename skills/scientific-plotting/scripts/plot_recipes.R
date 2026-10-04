# Shared schemas; ggplot2 recipes with disclosed metrics and transformations.
.recipe_source <- sys.frame(1)$ofile
.recipe_catalog <- jsonlite::fromJSON(file.path(dirname(dirname(normalizePath(.recipe_source))), "assets", "recipe-catalog.json"), simplifyVector = FALSE)
.sp_or <- function(value, default) if (is.null(value)) default else value
.sp_probability <- function(values, name) if (any(values < 0 | values > 1)) stop(name, " must be in [0,1]")
.sp_qlog <- function(q, options) {
  .sp_probability(q, "q")
  if (any(q == 0) && is.null(options$q_floor)) stop("Zero q-values need explicit q_floor")
  floor <- .sp_or(options$q_floor, .Machine$double.xmin)
  if (floor <= 0 || floor > 1) stop("q_floor must be in (0,1]")
  -log10(pmax(q, floor))
}

classification_scientific_metrics <- function(data) {
  require_scientific_columns(data, c("truth", "score"), c("truth", "score"))
  .sp_probability(data$score, "score")
  if (!setequal(data$truth, c(0, 1))) stop("Binary truth needs both 0 and 1; 1 is positive")
  thresholds <- sort(unique(data$score), decreasing = TRUE)
  tp <- vapply(thresholds, function(t) sum(data$truth == 1 & data$score >= t), numeric(1))
  fp <- vapply(thresholds, function(t) sum(data$truth == 0 & data$score >= t), numeric(1))
  recall <- tp / sum(data$truth == 1); fpr <- fp / sum(data$truth == 0)
  precision <- tp / (tp + fp)
  xx <- c(0, fpr); yy <- c(0, recall)
  list(n = nrow(data), positives = sum(data$truth), prevalence = mean(data$truth),
       auroc = sum(diff(xx) * (head(yy, -1)+tail(yy, -1))/2),
       average_precision = sum(diff(c(0, recall))*precision), brier = mean((data$score-data$truth)^2),
       roc = data.frame(x = xx, y = yy), pr = data.frame(x = c(0, recall), y = c(1, precision)))
}

intersection_scientific_counts <- function(data) {
  require_scientific_unique(data, c("item", "set"))
  members <- lapply(split(as.character(data$set), data$item), sort)
  # JSON keys avoid delimiter collisions in scientific identifiers.
  keys <- vapply(members, function(x) jsonlite::toJSON(x, auto_unbox = FALSE), character(1))
  counts <- sort(table(keys), decreasing = TRUE)
  list(counts = counts, members = lapply(names(counts), jsonlite::fromJSON))
}

draw_scientific_recipe <- function(kind, data, preset = "science", options = list()) {
  schema <- .recipe_catalog[[kind]]
  if (is.null(schema)) stop("Unknown recipe: ", kind)
  require_scientific_columns(data, unlist(schema$columns), unlist(schema$numeric))
  report <- list(recipe = kind, n_rows = nrow(data))
  column <- if ("model" %in% unlist(schema$columns)) "model" else if ("group" %in% unlist(schema$columns)) "group" else NULL
  if (!is.null(column)) {
    observed <- unique(as.character(data[[column]]))
    levels <- unlist(.sp_or(options$levels, observed))
    if (!length(levels) || anyDuplicated(levels) || !all(observed %in% levels)) stop("Invalid category levels")
    colors <- .sp_or(options$colors, scientific_colors(levels, preset))
    colors <- unlist(colors)
    if (!all(levels %in% names(colors))) stop("Colors must cover every level")
    data[[column]] <- factor(data[[column]], levels = levels)
    report$category_colors <- as.list(colors)
    scales <- list(ggplot2::scale_colour_manual(values = colors, limits = levels, drop = FALSE),
                   ggplot2::scale_fill_manual(values = colors, limits = levels, drop = FALSE))
    if(kind %in% c("raincloud","paired","facet","prediction","ablation","benchmark","umap")) scales<-c(scales,list(
      ggplot2::scale_shape_manual(values = stats::setNames(c(16,17,15,18,3,4,8,1)[seq_along(levels)], levels))))
    if(kind %in% c("ribbon","roc","pr","calibration")) scales<-c(scales,list(
      ggplot2::scale_linetype_manual(values = stats::setNames(rep(c("solid","dashed","dotdash","dotted"), length.out = length(levels)), levels))))
  }
  theme <- scientific_theme(preset)
  foreground <- scientific_preset(preset)$foreground
  p <- NULL
  if (kind == "raincloud") {
    data$.position <- as.numeric(data$group)
    clouds <- lapply(seq_along(levels), function(i) {
      values <- data$value[data$group == levels[i]]
      if (length(values) < 3 || sd(values) == 0) return(NULL)
      density <- density(values, from = min(values), to = max(values))
      data.frame(x = c(i-0.13, i-0.13-density$y/max(density$y)*0.34, i-0.13),
                 value = c(min(values), density$x, max(values)), group = levels[i])
    })
    clouds <- do.call(rbind, clouds)
    p <- ggplot2::ggplot(data, ggplot2::aes(.position, value, colour = group))
    if (!is.null(clouds)) p <- p + ggplot2::geom_polygon(data = clouds, ggplot2::aes(x, value, fill = group, group = group), inherit.aes = FALSE, alpha = 0.25)
    counts <- data.frame(x = seq_along(levels), value = max(data$value), label = paste0("n=", as.integer(table(data$group))))
    p <- p + ggplot2::geom_boxplot(ggplot2::aes(group = group), width = 0.12, outlier.shape = NA, linewidth = 0.35) +
      ggplot2::geom_point(ggplot2::aes(x = .position + 0.23, shape = group), position = ggplot2::position_jitter(width = 0.08, height = 0, seed = .sp_or(options$seed,2026)), size = 1.2, alpha = 0.8) +
      ggplot2::geom_text(data = counts, ggplot2::aes(x, value, label = label), inherit.aes = FALSE, vjust = -1.2, size = 2.5, colour = foreground) +
      ggplot2::scale_x_continuous(breaks = seq_along(levels), labels = levels) + scales + ggplot2::labs(x = NULL, y = "Value")
  } else if (kind == "paired") {
    require_scientific_unique(data, c("subject", "group"))
    matrix <- scientific_matrix(data, "subject", "group", "value")
    if (!setequal(colnames(matrix), levels)) stop("Paired plot needs complete subjects across all conditions")
    p <- ggplot2::ggplot(data, ggplot2::aes(group, value)) +
      ggplot2::geom_line(ggplot2::aes(group = subject), alpha = 0.25, linewidth = 0.35, colour = foreground) +
      ggplot2::geom_point(ggplot2::aes(colour = group, shape = group), size = 1.6) + scales + ggplot2::labs(x = NULL, y = "Value")
    report$n_pairs <- nrow(matrix)
  } else if (kind == "ribbon") {
    if (is.null(options$interval_definition)) stop("ribbon requires interval_definition")
    require_scientific_unique(data, c("group", "x"))
    if (any(data$lower > data$mean | data$mean > data$upper)) stop("Intervals must contain the mean")
    p <- ggplot2::ggplot(data, ggplot2::aes(x, mean, colour = group, fill = group)) +
      ggplot2::geom_ribbon(ggplot2::aes(ymin = lower, ymax = upper), alpha = 0.18, colour = NA) +
      ggplot2::geom_line(ggplot2::aes(linetype = group), linewidth = 0.5) + scales + ggplot2::labs(y = "Mean")
    report$interval_definition <- options$interval_definition
  } else if (kind == "forest") {
    if (is.null(options$interval_definition)) stop("forest requires interval_definition")
    require_scientific_unique(data, "label")
    if (any(data$lower > data$effect | data$effect > data$upper)) stop("Intervals must contain the effect")
    data$label <- factor(data$label, levels = rev(unique(data$label)))
    p <- ggplot2::ggplot(data, ggplot2::aes(effect, label)) +
      ggplot2::geom_vline(xintercept = .sp_or(options$reference,0), linetype = 2, colour = "gray") +
      ggplot2::geom_segment(ggplot2::aes(x = lower, xend = upper, yend = label), linewidth = 0.4, colour = foreground) +
      ggplot2::geom_point(size = 1.7, colour = foreground) + ggplot2::labs(x = "Effect", y = NULL)
    report$interval_definition <- options$interval_definition
  } else if (kind %in% c("correlation", "dendrogram")) {
    matrix <- scientific_matrix(data, "sample", "feature", "value")
    if (nrow(matrix) < 3) stop("At least three samples required")
    if (kind == "correlation") {
      method <- .sp_or(options$correlation, "pearson")
      if (!method %in% c("pearson", "spearman")) stop("Unsupported correlation method")
      correlation <- cor(matrix, method = method)
      if (any(!is.finite(correlation))) stop("Constant columns produce undefined correlations")
      tidy <- as.data.frame(as.table(correlation)); names(tidy) <- c("row", "column", "value")
      p <- ggplot2::ggplot(tidy, ggplot2::aes(column, row, fill = value)) + ggplot2::geom_tile() +
        ggplot2::scale_fill_gradient2(low = "#2166AC", mid = "white", high = "#B2182B", limits = c(-1,1)) +
        ggplot2::labs(x = NULL, y = NULL, fill = paste(method, "r"))
      report$method <- method
    } else {
      method <- .sp_or(options$linkage, "average"); metric <- .sp_or(options$distance, "euclidean")
      if (method == "ward" && metric != "euclidean") stop("Ward requires Euclidean distance")
      clustering <- hclust(dist(matrix, method = metric), method = if (method == "ward") "ward.D2" else method)
      # Extract segments from a dendrogram without another dependency.
      segments <- list(); current <- 0
      walk <- function(node) {
        if (is.leaf(node)) {current <<- current+1; return(c(x=current,y=0))}
        children <- lapply(node, walk); height <- attr(node,"height")
        for (child in children) segments[[length(segments)+1]] <<- data.frame(x=child[1],y=child[2],xend=child[1],yend=height)
        xs <- vapply(children, function(v) v[1], numeric(1))
        segments[[length(segments)+1]] <<- data.frame(x=min(xs),y=height,xend=max(xs),yend=height)
        c(x=mean(xs),y=height)
      }
      walk(as.dendrogram(clustering))
      p <- ggplot2::ggplot(do.call(rbind,segments), ggplot2::aes(x,y,xend=xend,yend=yend)) + ggplot2::geom_segment(linewidth=0.4,colour=foreground) +
        ggplot2::scale_x_continuous(breaks=seq_len(nrow(matrix)),labels=rownames(matrix)[clustering$order]) + ggplot2::labs(x=NULL,y=paste(metric,"distance"))
      report$linkage <- method; report$distance <- metric
    }
  } else if (kind == "facet") {
    if (length(unique(data$facet)) > 6) stop("Split more than six facets into separate figures")
    p <- ggplot2::ggplot(data, ggplot2::aes(x,y,colour=group,shape=group)) + ggplot2::geom_point(size=1.2) +
      ggplot2::facet_wrap(~facet, scales=.sp_or(options$facet_scales,"fixed")) + scales +
      ggplot2::scale_x_continuous(n.breaks=3) + ggplot2::scale_y_continuous(n.breaks=3)
    report$facets <- unique(as.character(data$facet))
  } else if (kind %in% c("volcano", "ma")) {
    require_scientific_unique(data,"label")
    data$logq <- .sp_qlog(data$q,options)
    threshold <- .sp_or(options$q_threshold,0.05); effect_threshold <- .sp_or(options$effect_threshold,1)
    if (threshold <= 0 || threshold > 1 || effect_threshold < 0) stop("Invalid thresholds")
    selected <- data$q <= threshold & abs(data$log2fc) >= effect_threshold
    data$status <- factor(ifelse(selected & data$log2fc>0,"Up",ifelse(selected,"Down","Other")),levels=c("Other","Down","Up"))
    if (kind == "volcano") {
      p <- ggplot2::ggplot(data,ggplot2::aes(log2fc,logq,colour=status)) + ggplot2::geom_point(size=1.1,alpha=0.75) +
        ggplot2::geom_hline(yintercept=-log10(threshold),linetype=2,colour="gray",linewidth=0.3) +
        ggplot2::geom_vline(xintercept=c(-effect_threshold,effect_threshold),linetype=2,colour="gray",linewidth=0.3) +
        ggplot2::labs(x="log2 fold change",y="−log10 adjusted p")
    } else {
      if (any(data$mean_expression <= 0)) stop("MA log axis requires positive mean_expression")
      p <- ggplot2::ggplot(data,ggplot2::aes(mean_expression,log2fc,colour=status)) + ggplot2::geom_point(size=1.1,alpha=0.75) +
        ggplot2::scale_x_log10() + ggplot2::geom_hline(yintercept=0,colour="gray",linewidth=0.3) + ggplot2::labs(x="Mean expression",y="log2 fold change")
    }
    p <- p + ggplot2::scale_colour_manual(values=c(Up="#D55E00",Down="#0072B2",Other="#999999"),drop=FALSE)
    report$q_threshold <- threshold; report$effect_threshold <- effect_threshold; report$zero_q <- sum(data$q==0); report$q_floor <- options$q_floor
  } else if (kind == "enrichment") {
    require_scientific_unique(data,"term"); data$logq <- .sp_qlog(data$q,options)
    if (any(data$ratio<0|data$ratio>1|data$count<=0|data$count!=as.integer(data$count))) stop("Invalid ratios/counts")
    data$term <- factor(data$term,levels=rev(unique(data$term)))
    p <- ggplot2::ggplot(data,ggplot2::aes(ratio,term,size=count,colour=logq)) + ggplot2::geom_point(alpha=0.85) +
      ggplot2::scale_colour_viridis_c() + ggplot2::scale_size_area(max_size=5) + ggplot2::labs(x="Gene ratio",y=NULL,colour="−log10\nadjusted p",size="Count")
  } else if (kind == "upset") {
    intersections <- intersection_scientific_counts(data)
    maximum <- .sp_or(options$max_intersections,12)
    if (maximum < 1 || maximum != as.integer(maximum)) stop("Invalid max_intersections")
    keep <- seq_len(min(length(intersections$counts),maximum))
    top <- data.frame(x=keep,count=as.numeric(intersections$counts[keep]))
    sets <- sort(unique(as.character(data$set)))
    active <- do.call(rbind,lapply(keep,function(i) data.frame(x=i,y=match(intersections$members[[i]],sets))))
    inactive <- expand.grid(x=keep,y=seq_along(sets))
    p1 <- ggplot2::ggplot(top,ggplot2::aes(x,count)) + ggplot2::geom_col(fill="#0072B2",width=0.65) + theme +
      ggplot2::scale_x_continuous(limits=c(0.5,length(keep)+0.5),expand=c(0,0)) + ggplot2::labs(x=NULL,y="Intersection size") + ggplot2::theme(axis.text.x=ggplot2::element_blank(),axis.ticks.x=ggplot2::element_blank())
    p2 <- ggplot2::ggplot(inactive,ggplot2::aes(x,y)) + ggplot2::geom_point(colour="#CCCCCC",size=1) +
      ggplot2::geom_line(data=active,ggplot2::aes(group=x),linewidth=0.4,colour=foreground) + ggplot2::geom_point(data=active,size=1.4,colour=foreground) +
      ggplot2::scale_y_continuous(breaks=seq_along(sets),labels=sets) + ggplot2::scale_x_continuous(limits=c(0.5,length(keep)+0.5),expand=c(0,0)) +
      theme + ggplot2::labs(x=NULL,y=NULL) + ggplot2::theme(axis.text.x=ggplot2::element_blank(),axis.ticks.x=ggplot2::element_blank())
    p <- patchwork::wrap_plots(p1,p2,ncol=1,heights=c(2,1))
    report$total_items <- length(unique(data$item)); report$shown_items <- sum(top$count); report$total_intersections <- length(intersections$counts)
  } else if (kind == "heatmap") {
    matrix <- scientific_matrix(data,"row","column","value")
    method <- .sp_or(options$linkage,"average"); metric <- .sp_or(options$distance,"euclidean")
    if (method=="ward" && metric!="euclidean") stop("Ward requires Euclidean distance")
    cluster <- function(x) hclust(dist(x,method=metric),method=if(method=="ward") "ward.D2" else method)$order
    rows <- if (.sp_or(options$cluster_rows,TRUE) && nrow(matrix)>1) cluster(matrix) else seq_len(nrow(matrix))
    columns <- if (.sp_or(options$cluster_columns,TRUE) && ncol(matrix)>1) cluster(t(matrix)) else seq_len(ncol(matrix))
    matrix <- matrix[rows,columns,drop=FALSE]
    data$row <- factor(as.character(data$row),levels=rev(rownames(matrix))); data$column <- factor(as.character(data$column),levels=colnames(matrix))
    color_scale <- ggplot2::scale_fill_viridis_c()
    if (!is.null(options$center)) {
      span <- max(abs(matrix-options$center)); if (span==0) stop("Centered heatmap needs a nonzero range")
      color_scale <- ggplot2::scale_fill_gradient2(low="#2166AC",mid="white",high="#B2182B",midpoint=options$center,limits=options$center+c(-span,span))
    }
    p <- ggplot2::ggplot(data,ggplot2::aes(column,row,fill=value)) + ggplot2::geom_tile() + color_scale + theme +
      ggplot2::labs(x=NULL,y=NULL,fill="Value") + ggplot2::theme(panel.grid=ggplot2::element_blank(),axis.text.x=ggplot2::element_text(angle=45,hjust=1))
    annotations <- list(); strips <- list()
    annotation_levels <- sort(unique(unlist(lapply(intersect(c("row_group","column_group"),names(data)),function(field)as.character(data[[field]])))))
    annotation_colors <- if(length(annotation_levels))scientific_colors(annotation_levels,preset) else NULL
    if(length(annotation_levels)) {
      legend_data <- data.frame(Group=factor(annotation_levels,levels=annotation_levels))
      p <- p + ggplot2::geom_point(data=legend_data,ggplot2::aes(colour=Group),x=NA_real_,y=NA_real_,inherit.aes=FALSE,show.legend=TRUE,na.rm=TRUE) +
        ggplot2::scale_colour_manual(values=annotation_colors) + ggplot2::labs(colour="Annotation\ngroup") +
        ggplot2::guides(colour=ggplot2::guide_legend(override.aes=list(shape=15,size=3)))
    }
    for (field in c("row_group","column_group")) {
      if (!field %in% names(data)) next
      key <- if (field=="row_group") "row" else "column"
      require_scientific_columns(data,field)
      annotation <- unique(data[c(key,field)]); require_scientific_unique(annotation,key)
      colors <- annotation_colors
      annotations[[field]] <- list(colors=as.list(colors),mapping=as.list(stats::setNames(as.character(annotation[[field]]),as.character(annotation[[key]]))))
      if (field=="row_group") {
        strip <- ggplot2::ggplot(annotation,ggplot2::aes(x=1,y=.data[[key]],fill=.data[[field]])) + ggplot2::geom_tile() +
          ggplot2::scale_fill_manual(values=colors) + theme + ggplot2::theme(axis.text=ggplot2::element_blank(),axis.ticks=ggplot2::element_blank(),legend.position="none") + ggplot2::labs(x=NULL,y=NULL)
        strips$row <- strip
      } else {
        strip <- ggplot2::ggplot(annotation,ggplot2::aes(x=.data[[key]],y=1,fill=.data[[field]])) + ggplot2::geom_tile() +
          ggplot2::scale_fill_manual(values=colors) + theme + ggplot2::theme(axis.text=ggplot2::element_blank(),axis.ticks=ggplot2::element_blank(),legend.position="none") + ggplot2::labs(x=NULL,y=NULL)
        strips$column <- strip
      }
    }
    if(length(strips)==2) p<-patchwork::wrap_plots(patchwork::plot_spacer(),strips$column,strips$row,p,ncol=2,widths=c(0.06,1),heights=c(0.06,1)) else
      if(!is.null(strips$row))p<-patchwork::wrap_plots(strips$row,p,nrow=1,widths=c(0.06,1)) else
      if(!is.null(strips$column))p<-patchwork::wrap_plots(strips$column,p,ncol=1,heights=c(0.06,1))
    report$row_order <- rownames(matrix); report$column_order <- colnames(matrix); report$linkage <- method; report$distance <- metric; report$center <- options$center
    report$annotations <- annotations
  } else if (kind %in% c("roc","pr","calibration")) {
    curves <- list(); model_metrics <- list()
    for (model in levels) {
      subset <- data[as.character(data$model)==model,,drop=FALSE]
      if (!nrow(subset)) next
      metric <- classification_scientific_metrics(subset)
      if ("sample" %in% names(subset)) require_scientific_unique(subset,"sample")
      if (kind=="calibration") {
        bins <- .sp_or(options$bins,10); if(bins<2 || bins!=as.integer(bins)) stop("bins must be integer >= 2")
        subset$bin <- pmin(floor(subset$score*bins)+1,bins)
        curve <- aggregate(cbind(x=score,y=truth)~bin,data=subset,FUN=mean)
      } else curve <- metric[[kind]]
      curve$model <- model; curves[[model]] <- curve
      metric$roc <- NULL; metric$pr <- NULL; model_metrics[[model]] <- metric
    }
    curves <- do.call(rbind,curves); curves$model <- factor(curves$model,levels=levels)
    p <- ggplot2::ggplot(curves,ggplot2::aes(x,y,colour=model,linetype=model)) + ggplot2::geom_line(linewidth=0.5) + scales +
      ggplot2::coord_cartesian(xlim=c(0,1),ylim=c(0,1))
    if(kind=="pr") {
      baseline <- data.frame(model=factor(names(model_metrics),levels=levels),prevalence=vapply(model_metrics,function(m)m$prevalence,numeric(1)))
      p <- p + ggplot2::geom_hline(data=baseline,ggplot2::aes(yintercept=prevalence,colour=model),linetype=3,alpha=0.4,linewidth=0.3) + ggplot2::labs(x="Recall",y="Precision")
    } else {
      p <- p + ggplot2::geom_abline(slope=1,intercept=0,colour="gray",linetype=2,linewidth=0.3) +
        ggplot2::labs(x=if(kind=="roc")"False positive rate" else "Mean predicted probability",y=if(kind=="roc")"True positive rate" else "Observed positive fraction")
    }
    report$models <- model_metrics
  } else if (kind == "confusion") {
    levels <- unlist(.sp_or(options$class_levels,sort(unique(c(as.character(data$truth),as.character(data$prediction))))))
    if(!all(c(as.character(data$truth),as.character(data$prediction)) %in% levels)) stop("Unmapped classes")
    counts <- table(factor(data$truth,levels=levels),factor(data$prediction,levels=levels))
    tidy <- as.data.frame(counts); names(tidy)<-c("truth","prediction","count")
    p <- ggplot2::ggplot(tidy,ggplot2::aes(prediction,truth,fill=count)) + ggplot2::geom_tile() +
      ggplot2::geom_text(ggplot2::aes(label=count),size=2.7) + ggplot2::scale_fill_gradient(low="white",high="#56B4E9") + ggplot2::labs(x="Predicted",y="Observed",fill="Count")
    report$labels <- levels; report$counts <- lapply(seq_len(nrow(counts)),function(i)as.integer(counts[i,])); report$accuracy <- sum(diag(counts))/sum(counts)
  } else if (kind == "prediction") {
    p <- ggplot2::ggplot(data,ggplot2::aes(observed,predicted,colour=model,shape=model)) + ggplot2::geom_point(size=1.2,alpha=0.75) +
      ggplot2::geom_abline(slope=1,intercept=0,colour="gray",linetype=2,linewidth=0.3) + scales + ggplot2::labs(x="Observed",y="Predicted")
    report$models <- lapply(split(data,data$model),function(d) list(n=nrow(d),rmse=sqrt(mean((d$predicted-d$observed)^2)),mae=mean(abs(d$predicted-d$observed)),r2=if(nrow(d)>1&&var(d$observed)>0)1-sum((d$predicted-d$observed)^2)/sum((d$observed-mean(d$observed))^2) else NULL))
  } else if (kind == "ablation") {
    require_scientific_unique(data,c("model","component"))
    p <- ggplot2::ggplot(data,ggplot2::aes(value,component,colour=model,shape=model)) + ggplot2::geom_point(position=ggplot2::position_dodge(width=0.3),size=1.6) + scales +
      ggplot2::labs(x=.sp_or(options$value_label,"Score"),y=NULL)
  } else if (kind == "benchmark") {
    require_scientific_unique(data,c("model","metric"))
    p <- ggplot2::ggplot(data,ggplot2::aes(value,model,colour=model,shape=model)) + ggplot2::geom_point(size=1.6) +
      ggplot2::facet_wrap(~metric,scales="free_x") + scales + ggplot2::labs(x=NULL,y=NULL)
    report$facets <- unique(as.character(data$metric))
  } else if (kind == "network") {
    require_scientific_unique(data,c("source","target"))
    nodes <- sort(unique(c(as.character(data$source),as.character(data$target))))
    if("weight" %in% names(data)) require_scientific_columns(data,"weight","weight")
    directed <- .sp_or(options$directed,FALSE)
    if(!directed && anyDuplicated(vapply(seq_len(nrow(data)),function(i)jsonlite::toJSON(sort(c(as.character(data$source[i]),as.character(data$target[i])))),character(1)))) stop("Reciprocal undirected edges are duplicates")
    positions <- data.frame(node=nodes,x=cos(seq_along(nodes)*2*pi/length(nodes)),y=sin(seq_along(nodes)*2*pi/length(nodes)))
    data$x <- positions$x[match(data$source,nodes)]; data$y <- positions$y[match(data$source,nodes)]
    data$xend <- positions$x[match(data$target,nodes)]; data$yend <- positions$y[match(data$target,nodes)]
    p <- ggplot2::ggplot(data,ggplot2::aes(x,y,xend=xend,yend=yend)) +
      ggplot2::geom_segment(colour="gray",linewidth=0.35,arrow=if(directed)grid::arrow(length=grid::unit(1.2,"mm"),type="closed") else NULL) +
      ggplot2::geom_point(data=positions,ggplot2::aes(x,y),inherit.aes=FALSE,size=4,colour="#56B4E9") +
      ggplot2::geom_text(data=positions,ggplot2::aes(x,y,label=node),inherit.aes=FALSE,size=2.3) + ggplot2::coord_equal() + ggplot2::labs(x=NULL,y=NULL)
    report$nodes <- length(nodes); report$edges <- nrow(data); report$layout <- "circular"; report$directed <- directed; report$layout_uses_weights <- FALSE
  } else if (kind == "umap") {
    require_scientific_unique(data,"cell")
    p <- ggplot2::ggplot(data,ggplot2::aes(umap1,umap2,colour=group,shape=group)) + ggplot2::geom_point(size=1.1,alpha=0.8) + scales + ggplot2::labs(x="UMAP 1",y="UMAP 2")
    report$embedding <- "supplied coordinates; no embedding computed"
  } else if (kind == "dotplot") {
    require_scientific_unique(data,c("group","gene")); .sp_probability(data$fraction,"fraction")
    p <- ggplot2::ggplot(data,ggplot2::aes(gene,group,size=fraction,colour=mean_expression)) + ggplot2::geom_point() +
      ggplot2::scale_size_area(max_size=5,limits=c(0,1),breaks=c(0.25,0.5,1),labels=c("25%","50%","100%")) +
      ggplot2::scale_colour_viridis_c() + ggplot2::labs(x=NULL,y=NULL,size="Expressing",colour="Mean\nexpression")
  }
  if (is.null(p)) stop("Recipe not implemented: ",kind)
  if(!inherits(p,"patchwork")) p <- p + theme
  if(!inherits(p,"patchwork")) {
    labels <- options[intersect(names(options),c("title","xlabel","ylabel"))]
    names(labels)[names(labels)=="xlabel"] <- "x"; names(labels)[names(labels)=="ylabel"] <- "y"
    if(length(labels)) p <- p + do.call(ggplot2::labs,labels)
    if(!is.null(options$xlim)||!is.null(options$ylim)) p <- p + ggplot2::coord_cartesian(xlim=unlist(options$xlim),ylim=unlist(options$ylim))
  } else if(!is.null(options$title)) p <- p + patchwork::plot_annotation(title=options$title)
  if(!is.null(options$inset)) {
    if(!kind %in% c("ribbon","prediction","umap")) stop("Zoom inset supports ribbon, prediction and umap")
    zoom_options <- options; zoom_options$inset <- NULL; zoom_options$title <- NULL
    zoom_options$xlim <- options$inset$xlim; zoom_options$ylim <- options$inset$ylim
    zoom <- draw_scientific_recipe(kind,data,preset,zoom_options)$plot + ggplot2::theme(legend.position="none",axis.title=ggplot2::element_blank(),axis.text=ggplot2::element_text(size=6))
    zoom <- zoom + ggplot2::scale_x_continuous(n.breaks=3) + ggplot2::scale_y_continuous(n.breaks=3)
    bounds <- unlist(.sp_or(options$inset$bounds,c(0.55,0.12,0.4,0.4)))
    p <- p + patchwork::inset_element(zoom,left=bounds[1],bottom=bounds[2],right=bounds[1]+bounds[3],top=bounds[2]+bounds[4],align_to="panel")
  }
  list(plot=p,report=report)
}
