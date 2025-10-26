# VSNet Helper Usage

The `vsnet` helper script lives in this directory and is not installed globally. Run it
with Python from the repo checkout, for example:

```bash
cd sonic-mgmt/spytest/vsnet
python3 vsnet --help
```

If you prefer to call it directly, prefix the command with `./` so the shell can locate
it:

```bash
./vsnet build --help
```

## Passing the `--host` value

VSNet forwards the `--host` argument directly to Docker via the standard `DOCKER_HOST`
environment variable. Provide any Docker-supported endpoint string (`unix://…`,
`tcp://…`, or `ssh://…`) without additional separators. For example, to reuse the local
Docker daemon you can rely on the default or pass the socket explicitly:

```bash
./vsnet build --host unix:///var/run/docker.sock
```

When targeting a remote daemon, use the same URLs Docker itself accepts, such as
`tcp://192.0.2.10:2375` or `ssh://builder@example.com`. Avoid inserting a pipe (`|`) in
the value—`build.sh` exports the string verbatim and the shell would interpret the pipe
as a command separator, yielding an error like `unix:///var/run/docker.sock: No such file
or directory`.

## Supplying SONiC images

VSNet mounts SONiC images from the host into the helper container before it launches the
virtual DUTs. By default the helper looks for the VS QCOW image at
`/data/images/sonic-vs.img` on the host (the `--share` directory, plus the `images`
subfolder). Copy or symlink your desired `sonic-vs.img` into that location before running
`vsnet build`/`vsnet topo`/`vsnet test` and the script will make it available under
`/images/default` inside the container. When overriding the share directory, point it at
the parent folder (for example `--share /mnt/sonic-data`) so that the helper can append
`images/sonic-vs.img`. If your artifact lives elsewhere, pass the absolute file path with
`--image default /path/to/sonic-vs.img`.

The helper now validates every image path before the container starts. If the resolved
path does not exist or expands to a directory (which happens when Docker creates a
placeholder because the file is missing), `vsnet` exits early with a message explaining
how to correct the location. This prevents opaque `cp: -r not specified; omitting
directory '/images/default'` errors later in the run.

If you want to keep images elsewhere, pass `--share /path/to/storage` so that the helper
mounts `/path/to/storage/images/sonic-vs.img` instead. You can also point individual DUTs
at different images by adding overrides such as `D1IMAGE=/path/to/sonic-vs-202411.img` in
the topology string; VSNet will bind-mount each referenced file under `/images/<name>` and
use it for the corresponding virtual device.

## Building and launching a simple topology

Once the helper image is built and your SONiC VS artifact is in place, you can ask VSNet to
instantiate a specific layout. The first positional argument selects the operation; pass
`topo` to create the virtual devices and links defined in the topology string. For example,
to bring up two DUTs connected to each other and to a Scapy traffic generator (`D1D2:2
D1T1:2`) run:

```bash
./vsnet topo --topology "D1D2:2 D1T1:2"
```

VSNet will generate the libvirt XML, start the VMs, create the veth pairs toward the Scapy
namespace, and write the resulting SpyTest `testbed.yaml` plus log files under the
`--share` directory (by default `/data`). The helper now launches the management container
with Docker's host cgroup namespace and tmpfs-backed `/run`/`/run/lock` mounts so that
systemd-managed services such as `libvirtd`, `openvswitch-switch`, and the Scapy traffic
generator can start successfully. Ensure your Docker Engine supports `--cgroupns host`
(Docker 20.10 or newer). If you already have an instance running and only need the topology
artifacts without recreating the host container, omit the earlier `build` step and call
`topo` directly.
