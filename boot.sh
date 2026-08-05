#!/bin/bash

# Container boot. Runs as root: reconciles mount ownership, preflights the
# nginx config, then drops privileges for good. (entrypoint.sh, despite the
# name, is the Flask launcher that supervisord runs as a child program.)

# SDS-owned state, created before anything opens log files there — the nginx
# and supervisord log paths are fixed at /sds/data/state/logs regardless of
# SDS_DATA_DIR. Ownership reconciliation covers host mounts written as root
# by older deployments; it may no-op on root-squashed NFS, where nothing is
# root-owned anyway.
mkdir -p /sds/data/state/logs
chown -R sds:sds /sds/data || true

AS_SDS=(setpriv --reuid sds --regid sds --init-groups)

# Validate the nginx config as the runtime user before handing anything to
# supervisord. Under supervisord a config-load failure just restart-loops
# nginx with the error buried in a log file; failing here puts the cause and
# the fix straight into the container logs. Running the check unprivileged
# matters: file-permission problems (SSL keys, log paths, missing SELinux
# labels on a mount) are invisible to root.
if ! preflight_output=$("${AS_SDS[@]}" nginx -t 2>&1); then
    echo "ERROR: nginx cannot start with the current configuration:"
    echo ""
    echo "$preflight_output"
    if echo "$preflight_output" | grep -qi 'permission denied' \
        && echo "$preflight_output" | grep -qiE 'ssl|certificate'; then
        echo ""
        echo "This looks like a file-permission problem on the SSL files."
        echo "All container processes run as UID 1000, so host-mounted"
        echo "certificates must be readable by UID 1000. On the host, run:"
        echo ""
        echo "    chown -R 1000:1000 ./ssl    # the directory mounted at /etc/nginx/ssl"
        echo "    chmod 400 ./ssl/key.pem"
        echo ""
        echo "then restart the container."
    fi
    exit 1
fi

# Configs from before the single-data-mount layout log under
# /var/log/supervisor. They still work, but only inside the container.
if "${AS_SDS[@]}" nginx -T 2>/dev/null | grep -q '^[^#]*/var/log/supervisor/'; then
    echo "NOTICE: the nginx config writes its logs under /var/log/supervisor."
    echo "That works, but those logs stay inside the container. Point them at"
    echo "/sds/data/state/logs/ to get persistent logs under ./data/state/logs/"
    echo "on the host."
fi

exec env HOME=/home/sds USER=sds LOGNAME=sds \
    "${AS_SDS[@]}" /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
