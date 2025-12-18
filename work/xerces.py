from dataportal import DataportalClient
import pandas

#
# A simple helper function to access a (hard-coded) log from the portal
#
def get_log() -> pandas.DataFrame:
    """
    Return a Xerces log file as a pandas DataFrame.
    Xerces is a cloud service, built using OpenStack, consisting of subsystem modules. 
    The log entries are tagged with the name of the emitting module.

    The modules are:
    - 'Nova' handles virtual machines.
    - 'Neutron' provides "networking-as-a-service".
    - 'Swift' provides an object storage.
    - 'Cinder' offers persistent block storage.
    - 'Horizon' is the GUI for OpenStack.
    - 'Keystone' provides identity services.
    - 'Glance' handle discovery and retrieve of virtual machine images.
    - 'Heat' orchestrates multiple composite cloud applications.

    Args:
        None 

    Returns:
        pandas.DataFrame: the Xerces log file as a pandas DataFrame
    """

    client = DataportalClient()
    client.fromDataset('ERDClogs-parsed')
    return client.getData(fileID=36666)
    
