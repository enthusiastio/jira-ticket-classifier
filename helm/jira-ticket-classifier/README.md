# Jira Ticket Classifier Helm Chart

This Helm chart deploys the Jira Ticket Classifier application on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (if persistence is enabled)

## Installing the Chart

To install the chart with the release name `jira-classifier`:

```bash
helm install jira-classifier ./jira-ticket-classifier \
  --set env.OPENAI_API_KEY=your-api-key \
  --set env.JIRA_HOST=https://your-jira-instance.atlassian.net \
  --set env.JIRA_USER=your-jira-username \
  --set env.JIRA_PASSWORD=your-jira-password
```

## Using NFS storage

To configure the chart to use NFS for the configuration directory:

```bash
helm install jira-classifier ./jira-ticket-classifier \
  --set env.OPENAI_API_KEY=your-api-key \
  --set env.JIRA_HOST=https://your-jira-instance.atlassian.net \
  --set env.JIRA_USER=your-jira-username \
  --set env.JIRA_PASSWORD=your-jira-password \
  --set nfs.enabled=true \
  --set nfs.server=your-nfs-server-ip \
  --set nfs.path=/exported/path
```

## Parameters

### Global parameters

| Name                      | Description                                     | Value           |
| ------------------------- | ----------------------------------------------- | --------------- |
| `replicaCount`            | Number of replicas                              | `1`             |
| `image.repository`        | Image repository                                | `jira-ticket-classifier` |
| `image.pullPolicy`        | Image pull policy                               | `IfNotPresent`  |
| `image.tag`               | Image tag                                       | `latest`        |

### Environment variables

| Name                      | Description                                     | Value           |
| ------------------------- | ----------------------------------------------- | --------------- |
| `env.OPENAI_API_KEY`      | OpenAI API Key for machine learning features    | `""`            |
| `env.JIRA_HOST`           | JIRA host URL                                   | `""`            |
| `env.JIRA_USER`           | JIRA username                                   | `""`            |
| `env.JIRA_PASSWORD`       | JIRA password or token                          | `""`            |

### Storage Configuration

| Name                      | Description                                     | Value           |
| ------------------------- | ----------------------------------------------- | --------------- |
| `nfs.enabled`             | Enable NFS storage for configuration            | `false`         |
| `nfs.server`              | NFS server address                              | `""`            |
| `nfs.path`                | NFS exported path                               | `""`            |
| `nfs.mountPath`           | Mount path in container                         | `/app/configuration` |
| `nfs.readOnly`            | Mount NFS as read-only                          | `false`         |
| `persistence.enabled`      | Enable PVC for configuration (if NFS disabled)  | `true`          |
| `persistence.storageClass` | PVC Storage Class                              | `""`            |
| `persistence.accessMode`   | PVC Access Mode                                | `ReadWriteOnce` |
| `persistence.size`         | PVC Storage Request                            | `1Gi`           |