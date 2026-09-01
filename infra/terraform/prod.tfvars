project_id   = "ai-holding-prod-bc"
region       = "southamerica-east1"
service_name = "holding-control-plane"

# deploy_service and image_ref are supplied by CI/CD.
# Production images are deployed by immutable digest, never by latest.
