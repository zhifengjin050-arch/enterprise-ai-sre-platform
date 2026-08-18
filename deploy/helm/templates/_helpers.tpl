{{- /*
Enterprise AI DevOps Platform v3.0.0 - Helm Helpers
SPDX-License-Identifier: MIT
*/}}

{{- /*
Expand the name of the chart.
*/}}
{{- define "ai-devops-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- /*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ai-devops-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- /*
Create chart name and version as used by the chart label.
*/}}
{{- define "ai-devops-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- /*
Common labels
*/}}
{{- define "ai-devops-platform.labels" -}}
helm.sh/chart: {{ include "ai-devops-platform.chart" . }}
{{ include "ai-devops-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- /*
Selector labels
*/}}
{{- define "ai-devops-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ai-devops-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- /*
Create the name of the service account to use
*/}}
{{- define "ai-devops-platform.serviceAccountName" -}}
{{- if .Values.backend.serviceAccount.create }}
{{- default (include "ai-devops-platform.fullname" .) .Values.backend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.backend.serviceAccount.name }}
{{- end }}
{{- end }}

{{- /*
Backend labels
*/}}
{{- define "backend.labels" -}}
{{ include "ai-devops-platform.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{- /*
Backend selector labels
*/}}
{{- define "backend.selectorLabels" -}}
{{ include "ai-devops-platform.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{- /*
Frontend labels
*/}}
{{- define "frontend.labels" -}}
{{ include "ai-devops-platform.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{- /*
Frontend selector labels
*/}}
{{- define "frontend.selectorLabels" -}}
{{ include "ai-devops-platform.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{- /*
PostgreSQL labels
*/}}
{{- define "postgres.labels" -}}
{{ include "ai-devops-platform.labels" . }}
app.kubernetes.io/component: postgres
{{- end }}

{{- /*
PostgreSQL selector labels
*/}}
{{- define "postgres.selectorLabels" -}}
{{ include "ai-devops-platform.selectorLabels" . }}
app.kubernetes.io/component: postgres
{{- end }}

{{- /*
Redis labels
*/}}
{{- define "redis.labels" -}}
{{ include "ai-devops-platform.labels" . }}
app.kubernetes.io/component: redis
{{- end }}

{{- /*
Redis selector labels
*/}}
{{- define "redis.selectorLabels" -}}
{{ include "ai-devops-platform.selectorLabels" . }}
app.kubernetes.io/component: redis
{{- end }}

{{- /*
Generate the backend environment variables from configmap and secret references.
*/}}
{{- define "backend.envVars" -}}
{{- if .Values.backend.extraEnv }}
{{ toYaml .Values.backend.extraEnv }}
{{- end }}
- name: SILICONFLOW_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "ai-devops-platform.fullname" . }}-secrets
      key: siliconflow-api-key
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "ai-devops-platform.fullname" . }}-secrets
      key: openai-api-key
- name: DEEPSEEK_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "ai-devops-platform.fullname" . }}-secrets
      key: deepseek-api-key
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "ai-devops-platform.fullname" . }}-secrets
      key: postgres-password
- name: JWT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "ai-devops-platform.fullname" . }}-secrets
      key: jwt-secret
{{- end }}

{{- /*
Generate the PostgreSQL connection string with password substitution.
*/}}
{{- define "postgres.url" -}}
{{- $host := "ai-devops-postgres" -}}
{{- printf "postgresql://devops:$(POSTGRES_PASSWORD)@%s:5432/devops_agent" $host -}}
{{- end }}