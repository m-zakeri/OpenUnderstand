# from multiprocessing import cpu_count, Pool
from ounderstand.parsing_process import process_file, get_files
def runner(path_project: str = ""):
    files = get_files(path_project)
    for item in files:
        process_file(item)
    # with Pool(cpu_count()) as pool:
    # pool.map_async(process_file, files)
    # pool.close()
    # pool.join()

