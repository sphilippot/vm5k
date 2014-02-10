from vm5k_engine import *
from itertools import product, repeat


class MicroArchBenchmark( vm5k_engine ):
    """ An execo engine that performs migration time measurements with
    various cpu/cell usage conditions and VM colocation. """

    def __init__(self):
        super(MicroArchBenchmark, self).__init__()
        self.env_name = 'wheezy-x64-base'
        self.stress_time = 300
        self.default_memory = 512
        self.options_parser.add_option("--mem", dest = "cachebench",
                    help = "", action = "store_true")
	self.options_parser.add_option("--membw", dest = "mbw",
                    help = "", action = "store_true")
        self.options_parser.add_option("--nomulti", dest = "nomulti",
                    help = "", action = "store_true")

    def define_parameters(self):
        """ Create the parameters for the engine :
        - distribution of VM
        - properties of the multicore VM
        """
        cluster = self.cluster
        n_vm = 3

        self.cpu_topology = get_cpu_topology(cluster, dir = self.result_dir)

        n_core = len(self.cpu_topology[0])
        n_cell = len(self.cpu_topology)

        base_dist = list( product( range(0, n_vm+1), repeat=n_core))

        dists = []
        for cell_dist in base_dist:
            tmp_dist = ''.join( [ str(i) for i in sorted(list(cell_dist), reverse=True) ])
            one_cell = tmp_dist +'0'*(n_cell-1)*n_core
            if one_cell not in dists:
                dists.append(one_cell)

            for i in range(n_cell):
                other_cell = ''.join( [ str(k) for k in [item for sublist in list(repeat(tmp_dist, i+1)) for item in sublist ] ] )+(n_cell-i-1)*n_core*'0'
                if other_cell not in dists:
                    dists.append(other_cell)

        mult_cpu_vm = []
        if self.options.nomulti:
            mult_cpu_vm.append('0'*(n_core))
        else:
            for i in range(n_core+1):
                mult_cpu_vm.append( '1'*i+'0'*(n_core-i))
            mult_cpu_vm.remove('1'+'0'*(n_core-1))

        parameters = {'dist': dists, 'multi_cpu': mult_cpu_vm}
        logger.debug(parameters)

        return parameters

    def workflow(self, comb, hosts, ip_mac):
        """ Perform a cpu stress on the VM """
        host = style.Thread(hosts[0].address.split('.')[0])
        comb_ok = False
        try:
            logger.info(style.step('Performing combination '+slugify(comb)+' on '+host))

            logger.info(host+': Destroying existing VMS')
            destroy_vms(hosts)
            logger.info(host+': Removing existing drives')
            rm_qcow2_disks(hosts)

            logger.info(host+': Defining virtual machines ')
            n_vm = self.comb_nvm(comb)
            if n_vm == 0:
                logger.warning('Combination '+slugify(comb)+' has no VM' )
                comb_ok = True
                exit()

            # Affecting a cpuset to each virtual machine
            cpu_index = [item for sublist in self.cpu_topology for item in sublist]
            cpusets = []
            n_mem = []
            for i in range(len(comb['dist'])):
                index = cpu_index[i]
                for j in range(int(comb['dist'][i])):
                    cpusets.append(str(index))
                    n_mem.append(str(self.default_memory))
            # Adding the multi_cpu vm if it exists
            n_cpu = sum( [ int(i) for i in comb['multi_cpu'] ])
            if n_cpu > 1:
                cpusets.append( ','.join( str(cpu_index[i]) for i in range(n_cpu) ) )
                multi_cpu = True
                n_mem.append(str(self.default_memory*n_cpu))
            else:
                multi_cpu = False

            n_cpus = 1 if not multi_cpu else [1]*(n_vm-1)+[n_cpu]
            vm_ids = ['vm-'+str(i+1) for i in range(n_vm)] if not multi_cpu else ['vm-'+str(i+1) for i in range(n_vm-1)]+['vm-multi']
#<<<<<<< HEAD
            vms = define_vms(vm_ids, ip_mac = ip_mac,
                             n_cpu = n_cpus, cpusets = cpusets, mem = n_mem)

            for vm in vms:
                vm['host'] = hosts[0]
#=======
            #if not self.options.cachebench:
                #vms = define_vms(vm_ids, ip_mac = ip_mac,
                #n_cpu = n_cpus, cpusets = cpusets, mem = n_mem)
            #else:
                #for vm in vms:
                    #vm['host'] = hosts[0]
#>>>>>>> c7fd7f7a6d401181fa4e0aa8ea11cb2cb6b6d874
            logger.info(', '.join( [vm['id']+' '+ vm['ip']+' '+str(vm['n_cpu'])+'('+vm['cpuset']+')' for vm in vms]))

            # Create disks, install vms and boot by core
            logger.info(host+': Creating disks')
            create = create_disks(vms).run()
            if not create.ok:
                logger.error(host+': Unable to create the VMS disks %s', slugify(comb))
                exit()
            logger.info(host+': Installing VMS')
            install = install_vms(vms).run()
            if not install.ok:
                logger.error(host+': Unable to install the VMS  %s', slugify(comb))
                exit()
            boot_successfull = boot_vms_by_core(vms)
            if not boot_successfull:
                logger.error(host+': Unable to boot all the VMS for %s', slugify(comb))
                exit()

            # Force pinning of vm-multi vcpus
            if multi_cpu:
                cmd = '; '.join( [ 'virsh vcpupin vm-multi '+str(i)+' '+str(cpu_index[i]) for i in range(n_cpu)] )
                vcpu_pin = SshProcess(cmd, hosts[0]).run()
                if not vcpu_pin.ok:
                    logger.error(host+': Unable to pin the vcpus of vm-multi %s', slugify(comb))
                    exit()
                    
            if self.options.cachebench:
#<<<<<<< HEAD
		## Force pinning of VM memory to CPU sets
		#for vm in vms:
		  #cmd = '; '.join( [ 'virsh numatune '+str(vm['id'])+' --mode strict --nodeset '+vm['cpuset']+' --live --current'] )
		  #vcpu_pin = SshProcess(cmd, hosts[0]).run()
		  #if not vcpu_pin.ok:
		      #logger.error(host+': Unable to pin the memory for vm %s  %s', (vm['id'], slugify(comb)))
		      #exit()
#=======
            ## Force pinning of VM memory to CPU sets
                for vm in vms:
                    cmd = '; '.join( [ 'virsh numatune '+str(vm['id'])+' --mode strict --nodeset '+vm['cpuset']+' --live --current'] )
                    vcpu_pin = SshProcess(cmd, hosts[0]).run()
                    if not vcpu_pin.ok:
                        logger.error(host+': Unable to pin the memory for vm %s  %s', (vm['id'], slugify(comb)))
                        exit()
#>>>>>>> c7fd7f7a6d401181fa4e0aa8ea11cb2cb6b6d874


            # Prepare virtual machines for experiments
            stress = []
            logger.info(host+': Installing kflops on vms and creating stress action')
            if self.options.cachebench:
	      stress.append( self.cpu_kflops([vm for vm in vms]) )
	    else:
	      stress.append( self.cpu_kflops([vm for vm in vms if vm['n_cpu'] == 1 ]) )

            if multi_cpu and not self.options.cachebench:
                logger.info(host+': Installing numactl and kflops on multicore vms')
                cmd =  'export DEBIAN_MASTER=noninteractive ; apt-get update && apt-get install -y  --force-yes numactl'
                inst_numactl = Remote( cmd, [vm['ip'] for vm in vms if vm['id'] == 'vm-multi']).run()
                if not inst_numactl.ok:
                    exit()
                self.cpu_kflops([vm for vm in vms if vm['id'] == 'vm-multi' ], install_only = True)
                for multi_vm in [vm for vm in vms if vm['id'] == 'vm-multi' ]:
                    for i in range(multi_vm['n_cpu']):
                        stress.append( Remote('numactl -C '+str(i)+' ./kflops/kflops > vm_multi_'+str(cpu_index[i])+'.out ',
                                            [multi_vm['ip']] ) )


            stress_actions = ParallelActions(stress)
            for p in stress_actions.processes:
                p.ignore_exit_code = p.nolog_exit_code = True

            logger.info(host+': Starting stress !! \n%s', pformat(stress) )
            stress_actions.start()
            for p in stress_actions.processes:
                if not p.ok:
                    logger.error(host+': Unable to start the stress for combination %s', slugify(comb))
                    exit()

            if not self.options.cachebench:
                sleep(self.stress_time)
                logger.info(host+': Killing stress !!')
                stress_actions.kill()
            else:
                logger.info(host+': Waiting for cachebench to finish.')
                for p in stress_actions.processes:
                    while not p.ended:
                        sleep(1)

            # Gathering results
            comb_dir = self.result_dir +'/'+ slugify(comb)+'/'
            try:
                mkdir(comb_dir)
            except:
                logger.warning(host+': %s already exists, removing existing files', comb_dir)
                for f in listdir(comb_dir):
                    remove(comb_dir+f)


            logger.info(host+': Retrieving file from VMs')
            vms_ip = [vm['ip'] for vm in vms if vm['n_cpu'] == 1]
            vms_out = [vm['ip']+'_'+vm['cpuset'] for vm in vms if vm['n_cpu'] == 1]
            comb_dir = self.result_dir +'/'+ slugify(comb)+'/'
            if self.options.cachebench:
                get_vms_output = Get(vms_ip, ['{{vms_out}}_rmw.out'], local_location = comb_dir).run()
                for p in get_vms_output.processes:
                    if not p.ok:
                        logger.error(host+': Unable to retrieve the files for combination %s', slugify(comb))
                        exit()
                get_vms_output = Get(vms_ip, ['{{vms_out}}_memcpy.out'], local_location = comb_dir).run()
                for p in get_vms_output.processes:
                    if not p.ok:
                        logger.error(host+': Unable to retrieve the files for combination %s', slugify(comb))
                        exit()
            else:
                get_vms_output = Get(vms_ip, ['{{vms_out}}.out'], local_location = comb_dir).run()
                for p in get_vms_output.processes:
                    if not p.ok:
                        logger.error(host+': Unable to retrieve the files for combination %s', slugify(comb))
                        exit()
            if multi_cpu:
                for multi_vm in [vm for vm in vms if vm['id'] == 'vm-multi' ]:
                    get_multi = Get([multi_vm['ip']], ['vm_multi_'+str(cpu_index[i])+'.out ' for i in range(multi_vm['n_cpu']) ],
                    local_location = comb_dir).run()
                    for p in get_multi.processes:
                        if not p.ok:
                            logger.error(host+': Unable to retrieve the vm_multi files for combination %s', slugify(comb))
                            exit()

            comb_ok = True
        finally:

            if comb_ok:
                self.sweeper.done( comb )
                logger.info(host+': '+slugify(comb)+' has been done')
            else:
                self.sweeper.cancel( comb )
                logger.warning(host+': '+slugify(comb)+' has been canceled')
            logger.info(style.step('%s Remaining'), len(self.sweeper.get_remaining()))


    def comb_nvm(self, comb):
        """Calculate the number of virtual machines in the combination"""
        n_vm = sum( [ int(i) for i in comb['dist'] ] )
        if sum( [ int(i) for i in comb['multi_cpu'] ]) > 1:
            n_vm += 1
        return n_vm

    def cpu_kflops(self, vms, install_only = False):
        """Put kflops.tgz on the hosts, compile it and optionnaly prepare a TaktukRemote"""
        mem_size = [str(27+int(vm['n_cpu'])) for vm in vms]
        vms_ip = [vm['ip'] for vm in vms]

        if self.options.cachebench:
            ChainPut(vms_ip, ['llcbench.tar.gz'] ).run()
            TaktukRemote( 'tar -xzf llcbench.tar.gz; cd llcbench; make linux-lam; make cache-bench', vms_ip).run()
            vms_out = [vm['ip']+'_'+vm['cpuset'] for vm in vms]
            if not install_only:
                return TaktukRemote('./llcbench/cachebench/cachebench -m {{memsize}} -e 1 -x 2 -d 1 -b > {{vms_out}}_rmw.out; ./llcbench/cachebench/cachebench -m {{memsize}} -e 1 -x 2 -d 1 -p > {{vms_out}}_memcpy.out', mem_size, vms_ip)  
            else:
                ChainPut(vms_ip, ['kflops.tgz'] ).run()
                TaktukRemote( 'tar -xzf kflops.tgz; cd kflops; make', vms_ip).run()
        vms_out = [vm['ip']+'_'+vm['cpuset'] for vm in vms]
        if not install_only:
            return TaktukRemote('./kflops/kflops > {{vms_out}}.out', vms_ip)
        



#    def mem_update(self, vms, size, speed):
#        """Copy, compile memtouch, calibrate and return memtouch action """
#
#        logger.debug('VMS: %s', pformat (vms) )
#        vms_ip = [Host(vm['ip']) for vm in vms]
#        #ChainPut(vms_ip, 'memtouch.tgz' ).run()
#        Put(vms_ip, 'memtouch.tgz' ).run()
#        Remote('tar -xzf memtouch.tgz; cd memtouch; gcc -O2 -lm -std=gnu99 -Wall memtouch-with-busyloop3.c -o memtouch-with-busyloop3',
#               vms_ip ).run()
#        calibration = SshProcess('./memtouch/memtouch-with-busyloop3 --cmd-calibrate '+str(size), vms_ip[0] ).run()
#        args = None
#        for line in calibration.stdout().split('\n'):
#            if '--cpu-speed' in line:
#                args = line
#        if args is None:
#            return False
#        logger.debug('%s', args)
#        return Remote('./memtouch/memtouch-with-busyloop3 --cmd-makeload '+args+' '+str(size)+' '+str(speed), vms_ip)
