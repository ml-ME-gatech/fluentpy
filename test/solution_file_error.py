from fluentpy.fluentio import SolutionFile

def main():

    with SolutionFile('test-files/trouble_solution_file_sam.trn') as sfile:
        df =sfile.readdf()
    
    print(df)

if __name__ == '__main__': 
    main()
