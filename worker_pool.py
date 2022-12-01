from multiprocessing import Pool


class WorkerPool:
    def __init__(self, limit):
        self.pool = Pool(limit)

    suc_result_list = []
    err_result_list = []

    def __suc_log_result(self, result):
        self.suc_result_list.append(result)

    def __err_log_result(self, error):
        self.err_result_list.append(error)

    def end_pool(self):
        self.pool.close()
        self.pool.join()

    def add_to_pool(self, func, args: tuple[str, str]):
        self.pool.apply_async(func, args, callback=self.__suc_log_result, error_callback=self.__err_log_result)

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)