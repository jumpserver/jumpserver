#!/bin/bash
#

for app in users assets perms apply_perms audits ops applications;do
    rm -f ../apps/$app/migrations/00*
done
