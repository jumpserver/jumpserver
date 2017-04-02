#!/bin/bash
#

for app in users assets perms audits ops applications;do
    rm -f ../apps/$app/migrations/00*
done
