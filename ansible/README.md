ansible/
├── ansible.cfg                    # Basic Ansible config
├── requirements.yml               # Collections needed
├── inventory.yml                  # Simple inventory file
├── vars/                         # Variables by environment
│   ├── dev.yml                   # Development variables
│   ├── staging.yml               # Staging variables
│   └── prod.yml                  # Production variables
├── playbooks/
│   └── store_backup.yml            # Your playbook
├── aws_credentials_setup.md       # AWS credentials setup guide
└── README.md                     # Basic documentation


setup:
```bash
ansible-galaxy install -r requirements.yml
ansible-playbook playbooks/s3-buckets.yml -i localhost
```
remove:
```bash
```