"""
BAEL Platform: Kubernetes Deployment Manifests
═════════════════════════════════════════════════════════════════════════════

Production-ready Kubernetes configuration for BAEL platform deployment.
Includes deployments, services, configmaps, and autoscaling.

This file documents the K8s structure that would be deployed.
For actual manifests, generate with: kubectl apply -f k8s/

Components:
• Deployments: API server, workers, services
• Services: ClusterIP, LoadBalancer, NodePort
• ConfigMaps: Configuration data
• Secrets: Sensitive data (encrypted)
• PersistentVolumes: Data persistence
• Autoscaling: HPA for CPU/memory
• Ingress: External access with TLS
"""

# ═══════════════════════════════════════════════════════════════════════════

# API Server Deployment

# ═══════════════════════════════════════════════════════════════════════════

API_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
name: bael-api-server
namespace: bael-production
labels:
app: bael
component: api-server
spec:
replicas: 3
strategy:
type: RollingUpdate
rollingUpdate:
maxSurge: 1
maxUnavailable: 0
selector:
matchLabels:
app: bael
component: api-server
template:
metadata:
labels:
app: bael
component: api-server
spec:
serviceAccountName: bael-api
containers: - name: api-server
image: bael:latest
imagePullPolicy: IfNotPresent
ports: - name: http
containerPort: 8000
protocol: TCP
env: - name: ENVIRONMENT
value: production - name: LOG_LEVEL
value: INFO - name: DATABASE_URL
valueFrom:
secretKeyRef:
name: bael-secrets
key: database-url
resources:
requests:
memory: "512Mi"
cpu: "500m"
limits:
memory: "2Gi"
cpu: "2000m"
livenessProbe:
httpGet:
path: /health
port: 8000
initialDelaySeconds: 30
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 3
readinessProbe:
httpGet:
path: /ready
port: 8000
initialDelaySeconds: 10
periodSeconds: 5
timeoutSeconds: 3
failureThreshold: 2
volumeMounts: - name: config
mountPath: /app/config
readOnly: true - name: logs
mountPath: /app/logs
volumes: - name: config
configMap:
name: bael-config - name: logs
emptyDir: {}
affinity:
podAntiAffinity:
preferredDuringSchedulingIgnoredDuringExecution: - weight: 100
podAffinityTerm:
labelSelector:
matchExpressions: - key: app
operator: In
values: - bael
topologyKey: kubernetes.io/hostname
"""

# ═══════════════════════════════════════════════════════════════════════════

# Worker Deployment (Task Processing)

# ═══════════════════════════════════════════════════════════════════════════

WORKER_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
name: bael-worker
namespace: bael-production
spec:
replicas: 5
selector:
matchLabels:
app: bael
component: worker
template:
metadata:
labels:
app: bael
component: worker
spec:
containers: - name: worker
image: bael:latest
command: ["python", "-m", "workers.task_executor"]
env: - name: WORKER_TYPE
value: task_processor - name: MAX_CONCURRENT_TASKS
value: "10"
resources:
requests:
memory: "1Gi"
cpu: "1000m"
limits:
memory: "4Gi"
cpu: "4000m"
volumeMounts: - name: work-dir
mountPath: /work
volumes: - name: work-dir
emptyDir: {}
"""

# ═══════════════════════════════════════════════════════════════════════════

# Service Definitions

# ═══════════════════════════════════════════════════════════════════════════

API_SERVICE = """
apiVersion: v1
kind: Service
metadata:
name: bael-api-service
namespace: bael-production
labels:
app: bael
spec:
type: LoadBalancer
sessionAffinity: ClientIP
sessionAffinityConfig:
clientIP:
timeoutSeconds: 3600
ports:

- name: http
  port: 80
  targetPort: 8000
  protocol: TCP
- name: https
  port: 443
  targetPort: 8443
  protocol: TCP
  selector:
  app: bael
  component: api-server
  """

INTERNAL_SERVICE = """
apiVersion: v1
kind: Service
metadata:
name: bael-internal
namespace: bael-production
spec:
type: ClusterIP
clusterIP: None
ports:

- name: metrics
  port: 9090
- name: health
  port: 8080
  selector:
  app: bael
  """

# ═══════════════════════════════════════════════════════════════════════════

# ConfigMap (Configuration)

# ═══════════════════════════════════════════════════════════════════════════

CONFIG_MAP = """
apiVersion: v1
kind: ConfigMap
metadata:
name: bael-config
namespace: bael-production
data:
config.yaml: |
server:
host: 0.0.0.0
port: 8000
workers: 4
timeout: 30

    database:
      pool_size: 20
      max_overflow: 40
      pool_recycle: 3600

    cache:
      backend: redis
      ttl: 3600
      max_size: 1000000

    logging:
      level: INFO
      format: json
      output: stdout

    security:
      cors_origins:
        - "https://app.bael.io"
      rate_limit: 1000
      auth_timeout: 3600

    features:
      neural_symbolic: true
      federated_learning: true
      quantum_ready: true
      advanced_autonomy: true
      consensus: true
      advanced_crypto: true

"""

# ═══════════════════════════════════════════════════════════════════════════

# Secret (Sensitive Data)

# ═══════════════════════════════════════════════════════════════════════════

SECRETS = """
apiVersion: v1
kind: Secret
metadata:
name: bael-secrets
namespace: bael-production
type: Opaque
stringData:
database-url: postgresql://user:pass@db.bael.svc:5432/bael
redis-url: redis://redis.bael.svc:6379
jwt-secret: your-secret-key-here-change-in-production
api-key: your-api-key-here
encryption-key: your-encryption-key-here
"""

# ═══════════════════════════════════════════════════════════════════════════

# Horizontal Pod Autoscaler

# ═══════════════════════════════════════════════════════════════════════════

HPA_CONFIG = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
name: bael-api-hpa
namespace: bael-production
spec:
scaleTargetRef:
apiVersion: apps/v1
kind: Deployment
name: bael-api-server
minReplicas: 3
maxReplicas: 10
metrics:

- type: Resource
  resource:
  name: cpu
  target:
  type: Utilization
  averageUtilization: 70
- type: Resource
  resource:
  name: memory
  target:
  type: Utilization
  averageUtilization: 80
  behavior:
  scaleDown:
  stabilizationWindowSeconds: 300
  policies: - type: Percent
  value: 100
  periodSeconds: 15
  scaleUp:
  stabilizationWindowSeconds: 0
  policies: - type: Percent
  value: 100
  periodSeconds: 15 - type: Pods
  value: 2
  periodSeconds: 60
  """

# ═══════════════════════════════════════════════════════════════════════════

# Ingress (External Access)

# ═══════════════════════════════════════════════════════════════════════════

INGRESS_CONFIG = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
name: bael-ingress
namespace: bael-production
annotations:
cert-manager.io/cluster-issuer: letsencrypt-prod
nginx.ingress.kubernetes.io/rate-limit: "100"
nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
ingressClassName: nginx
tls:

- hosts:
  - api.bael.io
    secretName: bael-tls
    rules:
- host: api.bael.io
  http:
  paths: - path: /
  pathType: Prefix
  backend:
  service:
  name: bael-api-service
  port:
  number: 80 - path: /health
  pathType: Exact
  backend:
  service:
  name: bael-api-service
  port:
  number: 8000
  """

# ═══════════════════════════════════════════════════════════════════════════

# Persistent Volume Claims (Data Storage)

# ═══════════════════════════════════════════════════════════════════════════

PVC_CONFIG = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
name: bael-data-pvc
namespace: bael-production
spec:
accessModes: - ReadWriteOnce
resources:
requests:
storage: 100Gi
storageClassName: fast-ssd

---

apiVersion: v1
kind: PersistentVolumeClaim
metadata:
name: bael-backup-pvc
namespace: bael-production
spec:
accessModes: - ReadWriteOnce
resources:
requests:
storage: 500Gi
storageClassName: standard
"""

# ═══════════════════════════════════════════════════════════════════════════

# Role-Based Access Control (RBAC)

# ═══════════════════════════════════════════════════════════════════════════

RBAC_CONFIG = """
apiVersion: v1
kind: ServiceAccount
metadata:
name: bael-api
namespace: bael-production

---

apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
name: bael-api-role
namespace: bael-production
rules:

- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]

---

apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
name: bael-api-binding
namespace: bael-production
roleRef:
apiGroup: rbac.authorization.k8s.io
kind: Role
name: bael-api-role
subjects:

- kind: ServiceAccount
  name: bael-api
  namespace: bael-production
  """

# ═══════════════════════════════════════════════════════════════════════════

# Monitoring & Observability

# ═══════════════════════════════════════════════════════════════════════════

PROMETHEUS_CONFIG = """
apiVersion: v1
kind: ConfigMap
metadata:
name: prometheus-config
namespace: bael-production
data:
prometheus.yml: |
global:
scrape_interval: 15s
evaluation_interval: 15s

    scrape_configs:
    - job_name: 'bael-api'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - bael-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: bael

"""

# ═══════════════════════════════════════════════════════════════════════════

# Deployment Instructions

# ═══════════════════════════════════════════════════════════════════════════

DEPLOYMENT_INSTRUCTIONS = """
KUBERNETES DEPLOYMENT GUIDE
════════════════════════════════════════════════════════════════════════════

Prerequisites:
• Kubernetes cluster (v1.24+)
• kubectl configured
• Helm (optional, for package management)
• Container registry access

Deployment Steps:

1. Create Namespace
   $ kubectl create namespace bael-production

2. Create Secrets
   $ kubectl create secret generic bael-secrets \\
   --from-literal=database-url='postgresql://...' \\
   --from-literal=redis-url='redis://...' \\
   -n bael-production

3. Apply ConfigMaps
   $ kubectl apply -f k8s/configmap.yaml

4. Apply RBAC
   $ kubectl apply -f k8s/rbac.yaml

5. Apply PersistentVolumes
   $ kubectl apply -f k8s/storage.yaml

6. Deploy API Server
   $ kubectl apply -f k8s/deployment-api.yaml

7. Deploy Workers
   $ kubectl apply -f k8s/deployment-workers.yaml

8. Deploy Services
   $ kubectl apply -f k8s/services.yaml

9. Setup Autoscaling
   $ kubectl apply -f k8s/hpa.yaml

10. Configure Ingress
    $ kubectl apply -f k8s/ingress.yaml

Verification:

# Check deployments

$ kubectl get deployments -n bael-production

# Check pods

$ kubectl get pods -n bael-production

# Check services

$ kubectl get svc -n bael-production

# Check HPA status

$ kubectl get hpa -n bael-production

# View logs

$ kubectl logs -f deployment/bael-api-server -n bael-production

# Port forwarding for testing

$ kubectl port-forward svc/bael-api-service 8000:80 -n bael-production

Scaling:

# Manual scaling

$ kubectl scale deployment bael-api-server --replicas=5 -n bael-production

# View HPA metrics

$ kubectl describe hpa bael-api-hpa -n bael-production

Monitoring:

# Get metrics

$ kubectl top nodes
$ kubectl top pods -n bael-production

# Setup Prometheus

$ kubectl apply -f k8s/prometheus.yaml

# Setup Grafana

$ kubectl apply -f k8s/grafana.yaml

Troubleshooting:

# Check pod status

$ kubectl describe pod <pod-name> -n bael-production

# View events

$ kubectl get events -n bael-production --sort-by='.lastTimestamp'

# Debug node issues

$ kubectl describe node <node-name>

Upgrade Procedure:

1. Build new image
2. Push to registry
3. Update deployment image
4. Kubectl applies rolling update
5. Monitor rollout
6. Rollback if needed

$ kubectl set image deployment/bael-api-server \\
bael=bael:v2.0 -n bael-production

$ kubectl rollout status deployment/bael-api-server -n bael-production

$ kubectl rollout undo deployment/bael-api-server -n bael-production
"""

if **name** == '**main**':
print(DEPLOYMENT_INSTRUCTIONS)
