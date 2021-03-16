from flask_sse import ServerSentEventsBlueprint


class SSEBlueprintNginx(ServerSentEventsBlueprint):
    def __init__(self):
        super().__init__('sse', __name__)

    def stream(self):
        response = super().stream()
        response.headers['X-Accel-Buffering'] = "no"  # for nginx to keep up connection
        return response


sse_nginx = SSEBlueprintNginx()
sse_nginx.add_url_rule(rule="", endpoint="stream", view_func=sse_nginx.stream)
