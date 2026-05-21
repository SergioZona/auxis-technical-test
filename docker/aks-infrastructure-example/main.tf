# ☁️ Azure Kubernetes Service (AKS) & PostgreSQL Infrastructure Provisioning
# This Terraform manifest defines the production-grade Azure resources for the Hybrid Agentic RAG Platform.
# DISCLAIMER: Not officially tested on Azure; use with caution.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# 2. Virtual Network & Subnets for Secure Isolation
resource "azurerm_virtual_network" "vnet" {
  name                = "rag-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "aks_subnet" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "db_subnet" {
  name                 = "db-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.2.0/24"]
  delegation {
    name = "fs-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# 3. Azure Container Registry (ACR) for Docker Image Hosting
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  admin_enabled       = false
}

# 4. Azure Kubernetes Service (AKS) Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "rag-platform"

  default_node_pool {
    name           = "systempool"
    node_count     = 2
    vm_size        = "Standard_D2s_v5" # Balanced general-purpose compute
    vnet_subnet_id = azurerm_subnet.aks_subnet.id
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }
}

# Grant AKS access to pull Docker images from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# 5. Private DNS Zone for Postgres Flexible Server Integration
resource "azurerm_private_dns_zone" "postgres_dns" {
  name                = "rag-postgres-private-dns.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "dns_vnet_link" {
  name                  = "postgres-dns-vnet-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres_dns.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

# 6. Azure Database for PostgreSQL (Flexible Server)
resource "azurerm_postgresql_flexible_server" "postgres" {
  name                   = var.postgres_server_name
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "16"
  delegated_subnet_id    = azurerm_subnet.db_subnet.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgres_dns.id
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  storage_mb             = 32768
  sku_name               = "GP_Standard_D2ds_v5" # General Purpose SKU with NVMe cache support

  depends_on = [azurerm_private_dns_zone_virtual_network_link.dns_vnet_link]
}

# Database definition inside the Flexible Server
resource "azurerm_postgresql_flexible_server_database" "prod_db" {
  name      = "app_prod"
  server_id = azurerm_postgresql_flexible_server.postgres.id
  colormap  = "SQL_Latin1_General_CP1_CI_AS"
}


# ==========================================
# VARIABLES DEFINITIONS
# ==========================================
variable "resource_group_name" {
  type        = string
  default     = "rag-platform-production-rg"
  description = "The name of the Resource Group where all resources will be provisioned."
}

variable "location" {
  type        = string
  default     = "eastus2"
  description = "Target Azure Region for low-latency scaling."
}

variable "acr_name" {
  type        = string
  default     = "ragregistryprod"
  description = "Unique name for the Azure Container Registry."
}

variable "aks_cluster_name" {
  type        = string
  default     = "rag-aks-production-cluster"
  description = "Name of the production Azure Kubernetes Service cluster."
}

variable "postgres_server_name" {
  type        = string
  default     = "rag-postgres-prod-server"
  description = "Unique host identifier for PostgreSQL Flexible Server."
}

variable "db_admin_username" {
  type        = string
  default     = "cloudadmin"
  description = "Database cluster root administrative username."
}

variable "db_admin_password" {
  type        = string
  sensitive   = true
  description = "Strong database administrator password (minimum 12 characters, alphanumeric)."
}


# ==========================================
# OUTPUTS
# ==========================================
output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "Deploy using kubectl by configuring context with this cluster name."
}

output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "Build and tag images with: docker build -t [acr_login_server]/ui:latest"
}

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.postgres.fqdn
  description = "Private Fully Qualified Domain Name of the PostgreSQL Flexible Server."
}
