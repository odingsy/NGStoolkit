library("reshape2")
args<-commandArgs(TRUE)
# f <- file("stdin")
d <- read.csv(args[1], header = T, sep="\t")
dd <- dcast(d, formula = chr + start + end + name + score + strand ~ treatment_title + TSNTS, value.var="count")
write.table(dd, file = args[2], sep="\t")