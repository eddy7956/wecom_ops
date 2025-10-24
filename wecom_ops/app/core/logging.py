import logging, json, sys

class JsonFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for k in ("trace_id", "route", "error_code", "latency_ms", "task_id", "wave", "batch"):
            v = getattr(record, k, None)
            if v is not None:
                base[k] = v
        return json.dumps(base, ensure_ascii=False)

def init_json_logger(level=logging.INFO):
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(level)
    return root
