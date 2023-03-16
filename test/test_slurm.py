from fluentpy.batch.fluent import FluentPBS,FluentSlurm
def main():


    print('\n\n')
    print('PBS\n')
    pbs = FluentPBS(WALLTIME = 6*60*60,
                    N_PROCESSORS= 4,
                    MEMORY= 4,
                    version = '2021R1',
                    specification= '2ddp',
                    account = 'GT-my14-paid')
    

    print(pbs.format_call())


    print('\n\n')
    print('Slurm\n')

    slurm = FluentSlurm(WALLTIME = 6*60*60,
                    N_PROCESSORS= 4,
                    MEMORY= 4,
                    version = '2021R1',
                    specification= '2ddp',
                    account = 'GT-my14-paid')
    
    print(slurm.format_call())
if __name__ == '__main__':
    main()