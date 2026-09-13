{{/*
One image reference by DIGEST, or a refusal. A tag would be a name for
whatever the registry holds today; a digest is the bytes stage tested.
*/}}
{{- define "demo.image" -}}
{{- $svc := index .Values.images .name -}}
{{- if or (not $svc.repository) (not $svc.digest) -}}
{{- fail (printf "images.%s.repository and images.%s.digest are required: the lab runs the digests stage tested, never a tag" .name .name) -}}
{{- end -}}
{{- printf "%s@%s" $svc.repository $svc.digest -}}
{{- end -}}

{{- define "demo.labels" -}}
app.kubernetes.io/part-of: aws-devops-sdet-demo
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "demo.roleArn" -}}
{{- $sa := index .Values.serviceAccounts .name -}}
{{- if not $sa.roleArn -}}
{{- fail (printf "serviceAccounts.%s.roleArn is required: without it the pods would run as the node (ADR-0097 D4)" .name) -}}
{{- end -}}
{{- $sa.roleArn -}}
{{- end -}}
