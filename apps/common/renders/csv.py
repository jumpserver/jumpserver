from rest_framework_csv.renderers import CSVStreamingRenderer


class JMSCSVRender(CSVStreamingRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        if renderer_context is None:
            renderer_context = {}
        view = renderer_context.get("view")
        if not view:
            return super().render(data, media_type=media_type,
                                  renderer_context=renderer_context)
        serializer = view.get_serializer()
        if not serializer:
            return super().render(data, media_type=media_type,
                                  renderer_context=renderer_context)
        request = renderer_context.get("request")
        if not request:
            return super().render(data, media_type=media_type,
                                  renderer_context=renderer_context)
        labels = {}
        header = []
        csv_fields = getattr(serializer.Meta, "csv_fields", None)

        for name, field in serializer.get_fields().items():
            if request.query_params.get('action') == 'import':
                if field.read_only:
                    continue
            else:
                if field.write_only:
                    continue
            if csv_fields and name not in csv_fields:
                continue
            header.append(name)
            if field.label:
                labels[name] = field.label
            else:
                labels[name] = name
        self.labels = labels
        self.header = header
        return super().render(data, media_type=media_type,
                              renderer_context=renderer_context)