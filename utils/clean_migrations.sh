#!/bin/bash
#

for app in users assets perms audits teminal ops;do
    rm -f $app/migrations/000*
done
