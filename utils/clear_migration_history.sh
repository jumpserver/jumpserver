#!/bin/bash
#

for app in users assets perms apply_perms audits ops applications;do
    python ../apps/manage.py migrate --fake $app zero
done
