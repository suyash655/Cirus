"""CIRUS — Validators: package init."""
from .rego_validator import validate_rego, ValidationResult as RegoValidationResult
from .terraform_validator import validate_terraform, ValidationResult as TerraformValidationResult

__all__ = ["validate_rego", "validate_terraform", "RegoValidationResult", "TerraformValidationResult"]
