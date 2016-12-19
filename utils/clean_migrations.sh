#!/bin/bash
#

for app in users assets perms audits teminal ops;do
    rm -f ../apps/$app/migrations/000*
done
