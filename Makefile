A2X = a2x
RM = rm -f

MAN_SRCs = networkd-dispatcher.txt
MAN_OUT  = $(MAN_SRCs:%.txt=%.8)

all: $(MAN_OUT)

clean:
	$(RM) $(MAN_OUT)

%.8: %.txt
	@$(A2X) --format manpage $<
