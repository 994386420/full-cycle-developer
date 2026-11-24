"""本地示例的提交入口。"""


class SubmitController:
    def __init__(self, send):
        self.send = send
        self.pending = False

    def submit(self):
        if self.pending:
            return False
        self.pending = True
        try:
            self.send(self.complete)
        except Exception:
            self.complete()
            raise
        return True

    def complete(self):
        self.pending = False
