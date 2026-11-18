# Security and publication boundaries

This repository performs static analysis. Do not execute its oracle Ansible,
Chef, or Puppet scripts against real infrastructure, and do not use benchmark
credentials in real services.

The author-supplied Chef sample
`chef-boneyard_qa-chef-server-cluster-attributes-default.rb` embeds an RSA private
key. That source file is excluded from this public repository and ignored by
Git. `prepare_data.py` restores the exact original from the authors' verified
artifact for local benchmarking only. Generated result text redacts private-key
payloads; this does not change file/line/category detections or numerical scores.

Historical artifact checksums and measured results are retained for provenance.
The local original dataset is not evidence that the embedded credentials are
safe or revoked. Do not remove the ignore rule or force-add that sample.

No deployment keys, account tokens, unrelated application configuration, or
virtual environments are intentionally included. Report a suspected exposure
privately to the repository owner rather than copying credential material into
a public issue.
