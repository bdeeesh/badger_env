from badger import environment
from pvaccess import *
import pvapy as pva
import numpy as np

from time import sleep


class Environment(environment.Environment):
    #SMOKE_TEST = False # do not write anything 

    name = 'RG2 quad'  # name of the environment
    variables = {  # variables and their hard-limited ranges
        'L1:RG2:Q1:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:Q2:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:Q3:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:Q4:SetDacCurrentC': [-2.0, 2.0],
        'L1:Q3:SetDacCurrentC': [-2.0, 2.0],
        'L1:Q4:SetDacCurrentC': [-2.0, 2.0],
        'L1:Q5:SetDacCurrentC': [-2.0, 2.0],
    }
    observables = ['L3:CM1:measCurrentCM','L5:CM1:measCurrentCM' ]  # measurements
    # test values before reading
    _test_variables = {'L1:RG2:KIK:chargeTrigC' : [0.5,1.0]}
    def get_variables(self,variable_names):
        """
        input is a list
        get pvs but first check if the conditons are met
        need to implement a method to check if the channel is connected 
        """
        channels = pva.MultiChannel(variable_names, pva.CA)
        get_value = [v[0]['value'] for v in channels.get().toDict()['value']]
        return {variable_names[k]: get_value[k] for k in range(len(variable_names))}


    def set_variables(self,variable_inputs: dict[str, float]):
        """
        Set PVs and verify their values.

        Parameters:
            variable_inputs (dict[str, float]): A dictionary mapping PV names to values.

        Raises:
            Exception: If the values could not be set after retries.
        """
        
        TEST_RUN = True
        if TEST_RUN:
            return None
        else:
            pass
        values =  list(variable_inputs.values())
        channels = pva.MultiChannel(list(variable_inputs.keys()), pva.CA)
        channels.putAsDoubleArray(values)
        verify = False

        """
         try to verify variables 
         3 x attempts
        """
        for i in range(3):
            print(f'verifying attempt {i}')
            sleep(0.1)
            new_values = [v[0]['value'] for v in channels.get().toDict()['value']]
            verify = np.isclose(new_values,values,atol=1e-3).all()
            if verify:
                break
            else:
                pass
        if verify:
            print ('setting variables done')
            #return new_values
        else:
            print (new_values,variable_inputs.values())
            raise Exception("could not write values, check pvs")

 
    def get_observables(self,observable_names):
        """
        Retrieve observable values.

        Parameters:
            observable_names (list[str]): A list of observable PV names.
            _test_variables (dict): A dictionary mapping PV names to (min_val, max_val) tuples.

        Returns:
            dict[str, float]: A dictionary mapping observable names to their averaged values over time.
        """
        max_attempts = 10
        required_successful_readings = 5
        sleep_time = 0.5
        observed_values_list = []

        # Initialize channels for observables outside the loop
        channels = pva.MultiChannel(observable_names, pva.CA)

        for attempt in range(max_attempts):
            conditions = True
            # Check test conditions
            for key, (min_val, max_val) in _test_variables.items():
                current_value = pva.Channel(key, pva.CA).get()['value']
                if isinstance(current_value, dict):
                    current_value = current_value['index']
                if not min_val <= current_value <= max_val:
                    print(f'Condition not met for {key}: Expected between {min_val} and {max_val}, got {current_value}')
                    conditions = False
                    break  # Exit the condition check loop if a condition fails
            if conditions:
                # Retrieve observable values
                raw_values = channels.get().toDict()['value']
                observed_values = [v[0]['value'] for v in raw_values]
                observed_values_list.append(observed_values)
                if len(observed_values_list) >= required_successful_readings:
                    # Required number of successful readings collected
                    break
            # Sleep before the next attempt
            sleep(sleep_time)

        if len(observed_values_list) >= required_successful_readings:
            # Compute the average across successful readings
            observed_values_over_time = np.array(observed_values_list)
            averaged_values = np.average(observed_values_over_time, axis=0)
            return {observable_names[k]: averaged_values[k] for k in range(len(observable_names))}
        else:
            # Insufficient successful readings collected
            print('Insufficient successful readings after 10 attempts. Returning zero values.')
            return {observable_name: 0.0 for observable_name in observable_names} 
