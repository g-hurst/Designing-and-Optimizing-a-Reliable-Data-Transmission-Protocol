# Paths to student scripts
SENDER_PATH = "./sender.py"
RECEIVER_PATH = "./receiver.py"

SENDER_PORT = 22081
RECEIVER_PORT = 8002

# Runs the sender
run-sender:
	-kill -9 $$(lsof -t -i:$(SENDER_PORT))
	./$(SENDER_PATH) "$(config)"

# Runs the receiver
run-receiver:
	-kill -9 $$(lsof -t -i:$(RECEIVER_PORT))
	./$(RECEIVER_PATH) "$(config)"
