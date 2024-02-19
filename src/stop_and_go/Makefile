# Paths to student scripts
SENDER_PATH = "./sender_stop_and_go.py"
RECEIVER_PATH = "./receiver_stop_and_go.py"

SENDER_PORT = 8001
RECEIVER_PORT = 8002

# Runs the sender
run-sender:
	-kill -9 $$(lsof -t -i:$(SENDER_PORT))
	./$(SENDER_PATH) "$(config)"

# Runs the receiver
run-receiver:
	-kill -9 $$(lsof -t -i:$(RECEIVER_PORT))
	./$(RECEIVER_PATH) "$(config)"
