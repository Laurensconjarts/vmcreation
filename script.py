vm = None
vm_name = None
stub_config = None
boot_svc = None
cleardata = False
orig_boot_info = None
orig_cpu_info = None
cpu_svc = None
nics_to_delete = []
orig_nic_summaries = None
ethernet_svc = None

server, username, password, cleardata, skip_verification, vm_name = \
    parse_cli_args_vm(testbed.config['VM_NAME_DEFAULT'])
stub_config = vapiconnect.connect(server,
                                  username,
                                  password,
                                  skip_verification)

global vm
vm = get_vm(stub_config, vm_name)
if not vm:
    exit('Sample requires an existing vm with name ({}). '
         'Please create the vm first.'.format(vm_name))
print("Using VM '{}' ({}) for Disk Sample".format(vm_name, vm))

# Get standard portgroup to use as backing for sample
standard_network = network_helper.get_standard_network_backing(
    stub_config,
    testbed.config['STDPORTGROUP_NAME'],
    testbed.config['VM_DATACENTER_NAME'])

# Create Ethernet stub used for making requests
global ethernet_svc
ethernet_svc = Ethernet(stub_config)
vm_power_svc = Power(stub_config)
nic_summaries = ethernet_svc.list(vm=vm)

# Save current list of Ethernet adapters to verify that we have cleaned
# up properly
global orig_nic_summaries
orig_nic_summaries = nic_summaries

global nics_to_delete

# Create Ethernet Nic using STANDARD_PORTGROUP with the default settings
nic_create_spec = Ethernet.CreateSpec(
    backing=Ethernet.BackingSpec(
        type=Ethernet.BackingType.STANDARD_PORTGROUP,
        network=standard_network))
nic = ethernet_svc.create(vm, nic_create_spec)
nics_to_delete.append(nic)
nic_info = ethernet_svc.get(vm, nic)

# Create Ethernet Nic by using STANDARD_PORTGROUP
nic_create_spec = Ethernet.CreateSpec(
    start_connected=True,
    allow_guest_control=True,
    mac_type=Ethernet.MacAddressType.MANUAL,
    mac_address='01:23:45:67:89:10',
    wake_on_lan_enabled=True,
    backing=Ethernet.BackingSpec(
        type=Ethernet.BackingType.STANDARD_PORTGROUP,
        network=standard_network))
nic = ethernet_svc.create(vm, nic_create_spec)
nics_to_delete.append(nic)
nic_info = ethernet_svc.get(vm, nic)

# Update the Ethernet NIC with a different backing
nic_update_spec = Ethernet.UpdateSpec(
    backing=Ethernet.BackingSpec(
        type=Ethernet.BackingType.STANDARD_PORTGROUP,
        network=standard_network))
ethernet_svc.update(vm, nic, nic_update_spec)
nic_info = ethernet_svc.get(vm, nic)

# Update the Ethernet NIC configuration
nic_update_spec = Ethernet.UpdateSpec(
    wake_on_lan_enabled=False,
    mac_type=Ethernet.MacAddressType.GENERATED,
    start_connected=False,
    allow_guest_control=False)
ethernet_svc.update(vm, nic, nic_update_spec)
nic_info = ethernet_svc.get(vm, nic)

# Powering on the VM to connect the virtual Ethernet adapter to its backing
vm_power_svc.start(vm)
nic_info = ethernet_svc.get(vm, nic)

# Connect the Ethernet NIC after powering on the VM
ethernet_svc.connect(vm, nic)

# Disconnect the Ethernet NIC while the VM is powered on
ethernet_svc.disconnect(vm, nic)

def get_placement_spec_for_resource_pool(stub_config,
                                         datacenter_name,
                                         vm_folder_name,
                                         datastore_name):
    """
    Returns a VM placement spec for a resourcepool. Ensures that the
    vm folder and datastore are all in the same datacenter which is specified.
    """
    resource_pool = resource_pool_helper.get_resource_pool(stub_config,
                                                           datacenter_name)

    folder = folder_helper.get_folder(stub_config,
                                      datacenter_name,
                                      vm_folder_name)

    datastore = datastore_helper.get_datastore(stub_config,
                                               datacenter_name,
                                               datastore_name)

    # Create the vm placement spec with the datastore, resource pool and vm
    # folder
    placement_spec = VM.PlacementSpec(folder=folder,
                                      resource_pool=resource_pool,
                                      datastore=datastore)

    print("get_placement_spec_for_resource_pool: Result is '{}'".
          format(placement_spec))
    return placement_spec

def create_basic_vm(stub_config, placement_spec, standard_network):
    """
    Create a basic VM.

    Using the provided PlacementSpec, create a VM with a selected Guest OS
    and provided name.

    Create a VM with the following configuration:
    * Create 2 disks and specify one of them on scsi0:0 since it's the boot disk
    * Specify 1 ethernet adapter using a Standard Portgroup backing
    * Setup for PXE install by selecting network as first boot device

    Use guest and system provided defaults for most configuration settings.
    """
    guest_os = testbed.config['VM_GUESTOS']

    boot_disk = Disk.CreateSpec(type=Disk.HostBusAdapterType.SCSI,
                                scsi=ScsiAddressSpec(bus=0, unit=0),
                                new_vmdk=Disk.VmdkCreateSpec())
    data_disk = Disk.CreateSpec(new_vmdk=Disk.VmdkCreateSpec())

    nic = Ethernet.CreateSpec(
        start_connected=True,
        backing=Ethernet.BackingSpec(
            type=Ethernet.BackingType.STANDARD_PORTGROUP,
            network=standard_network))

    boot_device_order = [BootDevice.EntryCreateSpec(BootDevice.Type.ETHERNET),
                         BootDevice.EntryCreateSpec(BootDevice.Type.DISK)]

    vm_create_spec = VM.CreateSpec(name=vm_name,
                                   guest_os=guest_os,
                                   placement=placement_spec,
                                   disks=[boot_disk, data_disk],
                                   nics=[nic],
                                   boot_devices=boot_device_order)
    print('\n# Example: create_basic_vm: Creating a VM using spec\n-----')
    print(pp(vm_create_spec))
    print('-----')

    vm_svc = VM(stub_config)
    vm = vm_svc.create(vm_create_spec)

    print("create_basic_vm: Created VM '{}' ({})".format(vm_name, vm))

    vm_info = vm_svc.get(vm)
    print('vm.get({}) -> {}'.format(vm, pp(vm_info)))

    return vm

def run():
    global vm
    vm = get_vm(stub_config, vm_name)
    if not vm:
        exit('Sample requires an existing vm with name ({}). '
             'Please create the vm first.'.format(vm_name))
    print("Using VM '{}' ({}) for Boot Sample".format(vm_name, vm))

    # Create Boot stub used for making requests
    global boot_svc
    boot_svc = Boot(stub_config)

    print('\n# Example: Get current Boot configuration')
    boot_info = boot_svc.get(vm)
    print('vm.hardware.Boot.get({}) -> {}'.format(vm, pp(boot_info)))

    # Save current Boot info to verify that we have cleaned up properly
    global orig_boot_info
    orig_boot_info = boot_info

    print('\n# Example: Update firmware to EFI for Boot configuration')
    update_spec = Boot.UpdateSpec(type=Boot.Type.EFI)
    print('vm.hardware.Boot.update({}, {})'.format(vm, update_spec))
    boot_svc.update(vm, update_spec)
    boot_info = boot_svc.get(vm)
    print('vm.hardware.Boot.get({}) -> {}'.format(vm, pp(boot_info)))

    print('\n# Example: Update boot firmware to tell it to enter setup mode on '
          'next boot')
    update_spec = Boot.UpdateSpec(enter_setup_mode=True)
    print('vm.hardware.Boot.update({}, {})'.format(vm, update_spec))
    boot_svc.update(vm, update_spec)
    boot_info = boot_svc.get(vm)
    print('vm.hardware.Boot.get({}) -> {}'.format(vm, pp(boot_info)))

    print('\n# Example: Update boot firmware to introduce a delay in boot'
          ' process and to reboot')
    print('# automatically after a failure to boot. '
          '(delay=10000 ms, retry=True,')
    print('# retry_delay=30000 ms')
    update_spec = Boot.UpdateSpec(delay=10000,
                                  retry=True,
                                  retry_delay=30000)
    print('vm.hardware.Boot.update({}, {})'.format(vm, update_spec))
    boot_svc.update(vm, update_spec)
    boot_info = boot_svc.get(vm)
    print('vm.hardware.Boot.get({}) -> {}'.format(vm, pp(boot_info)))

def run_cpu():
    global vm
    vm = get_vm(stub_config, vm_name)
    if not vm:
        exit('Sample requires an existing vm with name ({}). '
             'Please create the vm first.'.format(vm_name))
    print("Using VM '{}' ({}) for Cpu Sample".format(vm_name, vm))

    # Create CPU stub used for making requests
    global cpu_svc
    cpu_svc = Cpu(stub_config)

    # Get the current CPU configuration
    cpu_info = cpu_svc.get(vm)
    print('vm.hardware.Cpu.get({}) -> {}'.format(vm, pp(cpu_info)))

    # Save current CPU info to verify that we have cleaned up properly
    global orig_cpu_info
    orig_cpu_info = cpu_info

    # Update the number of CPU cores of the virtual machine
    update_spec = Cpu.UpdateSpec(count=2)
    print('vm.hardware.Cpu.update({}, {})'.format(vm, update_spec))
    cpu_svc.update(vm, update_spec)

    # Get the new CPU configuration
    cpu_info = cpu_svc.get(vm)
    print('vm.hardware.Cpu.get({}) -> {}'.format(vm, pp(cpu_info)))

    # Update the number of cores per socket and
    # enable adding CPUs while the virtual machine is running
    update_spec = Cpu.UpdateSpec(cores_per_socket=2, hot_add_enabled=True)
    print('vm.hardware.Cpu.update({}, {})'.format(vm, update_spec))
    cpu_svc.update(vm, update_spec)