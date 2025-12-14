def sync(shared, curr_time_acc):
    sim_time_acc = curr_time_acc
    if hasattr(shared, "time_modified") and shared.time_modified:
        print(">> GUI requested time change")

        h = shared.sim_hour
        m = shared.sim_min
        d = shared.sim_day

        total_minutes = (d - 1) * 24 * 60 + h * 60 + m

        sim_time_acc = total_minutes * 60 

        shared.time_modified = False

    return sim_time_acc

def getDt(time, last_time):
    now = time.time()
    dt = now - last_time
    last_time = now

    return dt, last_time