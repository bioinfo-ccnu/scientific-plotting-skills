load_scientific_table <- function(path, columns = NULL, sheet = 1, reshape = NULL) {
  extension <- tolower(tools::file_ext(path))
  data <- switch(extension,
    csv = read.csv(path, check.names = FALSE),
    tsv = read.delim(path, check.names = FALSE),
    txt = read.delim(path, check.names = FALSE),
    xlsx = {if (!requireNamespace("readxl", quietly = TRUE)) stop("Install readxl"); as.data.frame(readxl::read_excel(path, sheet = sheet))},
    xlsm = {if (!requireNamespace("readxl", quietly = TRUE)) stop("Install readxl"); as.data.frame(readxl::read_excel(path, sheet = sheet))},
    stop("Input must be CSV, TSV or XLSX/XLSM")
  )
  if (!is.null(columns)) {
    sources <- unlist(columns, use.names = FALSE)
    if (anyDuplicated(sources) || !all(sources %in% names(data))) stop("Invalid column mapping")
    names(data)[match(sources, names(data))] <- names(columns)
    if (anyDuplicated(names(data))) stop("Column mapping created duplicate names")
  }
  if (!is.null(reshape)) data <- do.call(reshape_scientific_table, c(list(data = data), reshape))
  data
}

reshape_scientific_table <- function(data, mode, id_columns = NULL, value_columns = NULL,
                                     names_to = "variable", values_to = "value", index = NULL, columns = NULL, values = NULL) {
  if (mode == "long") {
    ids <- unlist(id_columns); selected <- unlist(value_columns)
    if (!length(ids) || !length(selected) || !all(c(ids, selected) %in% names(data))) stop("Long reshape needs valid ID/value columns")
    if (names_to %in% ids || values_to %in% ids || names_to == values_to) stop("Reshape names collide")
    return(do.call(rbind, lapply(selected, function(column) {
      result <- data[ids]; result[[names_to]] <- column; result[[values_to]] <- data[[column]]; result
    })))
  }
  if (mode == "wide") {
    ids <- unlist(index)
    if (!length(ids) || is.null(columns) || is.null(values)) stop("Wide reshape needs index, columns, values")
    require_scientific_unique(data, c(ids, columns))
    result <- unique(data[ids])
    for (level in unique(as.character(data[[columns]]))) {
      selected <- data[as.character(data[[columns]]) == level, c(ids, values), drop = FALSE]
      names(selected)[names(selected) == values] <- level
      result <- merge(result, selected, by = ids, all.x = TRUE, sort = FALSE)
    }
    return(result)
  }
  stop("reshape.mode must be long or wide")
}

require_scientific_columns <- function(data, columns, numeric = character()) {
  if (!nrow(data) || !all(columns %in% names(data))) stop("Empty input or missing columns: ", paste(setdiff(columns, names(data)), collapse = ", "))
  for (column in columns) if (anyNA(data[[column]])) stop("Missing values in ", column, "; resolve explicitly")
  for (column in numeric) if (!is.numeric(data[[column]]) || any(!is.finite(data[[column]]))) stop(column, " must contain finite numbers")
}

require_scientific_unique <- function(data, columns) {
  if (anyDuplicated(data[columns])) stop("Duplicate observations for key ", paste(columns, collapse = ", "))
}

scientific_matrix <- function(data, row, column, value) {
  require_scientific_unique(data, c(row, column))
  rows <- sort(unique(as.character(data[[row]]))); columns <- sort(unique(as.character(data[[column]])))
  result <- matrix(NA_real_, length(rows), length(columns), dimnames = list(rows, columns))
  result[cbind(match(as.character(data[[row]]), rows), match(as.character(data[[column]]), columns))] <- data[[value]]
  if (anyNA(result)) stop("Matrix is incomplete; resolve missing cells explicitly")
  result
}
