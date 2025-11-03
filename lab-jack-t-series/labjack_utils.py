from labjack import ljm


def setup_labjack_device(model, serial):
    print(model, serial)
    handle = ljm.openS(model, "USB", serial)
    info = ljm.getHandleInfo(handle)
    return handle, info


def configure_labjack_device(handle, info):
    deviceType = info[0]
    from labjack import ljm

    if deviceType == ljm.constants.dtT4:
        aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [0, 0]
    else:
        ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)
        ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)
        aNames = ["AIN0_RANGE", "AIN1_RANGE", "STREAM_RESOLUTION_INDEX"]
        aValues = [10.0, 10.0, 0]
        if deviceType == ljm.constants.dtT7:
            aNames.extend(
                ["AIN0_NEGATIVE_CH", "STREAM_SETTLING_US", "AIN1_NEGATIVE_CH"]
            )
            aValues.extend([199, 0, 199])
    numFrames = len(aNames)
    ljm.eWriteNames(handle, numFrames, aNames, aValues)
    return handle
