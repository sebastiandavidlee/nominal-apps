# nominal python file structure

# imports
import connect_python # this is for the logger and main decorator

# set up logger for writing messages to console and debug/monitor
# logger.info(), logger.error()
logger = connect_python.get_logger(__name__)
# some mehtods used are .info(), .error(), .debug(), .warning()
# in contrast, the decorator helps script integrate w nominal connect

# functions

# pass main function as argument to connect_python
@connect_python.main    # this whole line is the decorator
# it tells python to pass the template_main function below to connect_python.main
# this decorator changes the function's behavior
# it's a simple way to add extra functionality without changing much
def template_main(connect_client: connect_python.Client): ...
    # some methods for connect_client are:
    # connect_client.stream(stream_name, timestamp, names=channel_names, values=channel_values)
    # connect_client.clear_stream(stream_name)
    # connect_client.get_parameter(name, default_value)
    # connect_client.set_parameter(name, value)

if __name__ == "__main__":
    template_main()

