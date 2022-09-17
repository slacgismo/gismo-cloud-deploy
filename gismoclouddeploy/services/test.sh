#!/bin/bash

# if eksctl get cluster | grep gcd-jimmy-cli-1663394353 ; then 
#     echo "MATCH"
# fi
rec="$(eksctl get cluster | grep gcd-jimmy-cli-1663394353)"
if [ -n "$rec" ] ; then echo gcd-jimmy-cli-1663394353; fi