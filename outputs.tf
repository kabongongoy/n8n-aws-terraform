output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.n8n.id
}

output "elastic_ip" {
  description = "Public Elastic IP address"
  value       = aws_eip.n8n.public_ip
}

output "n8n_url" {
  description = "n8n UI URL"
  value       = "https://${var.domain_name}"
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.n8n.public_ip}"
}
