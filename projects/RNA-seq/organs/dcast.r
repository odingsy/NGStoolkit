library("reshape2")
args<-commandArgs(TRUE)
f <- file("stdin")
d <- read.csv(f, header = T, sep="\t")
dd <- dcast(d, formula = chr + start + end + name + score + strand ~ treatment_title, value.var="count")
write.table(dd, file = args[1], sep="\t")