A2X = a2x

MAN_SRCs = networkd-dispatcher.txt
MAN_OUT  = $(MAN_SRCs:%.txt=%)

all: $(MAN_OUT)


%: %.txt
	@$(A2X) --format manpage $<
