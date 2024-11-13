from badger import environment
from pvaccess import *
import pvapy as pva
import numpy as np
import epics
from time import sleep


class Environment(environment.Environment):
    #SMOKE_TEST = False # do not write anything 

    name = 'linac'  # name of the environment
    variables = {  # variables and their hard-limited ranges
        'L1:RG2:Q1:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:Q2:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:Q3:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:Q4:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:V1:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:V2:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:V3:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:H2:SetDacCurrentC': [-2.0, 2.0],
        'L1:RG2:H3:SetDacCurrentC': [-2.0, 2.0],

        'L1:Q3:SetDacCurrentC': [-2.0, 2.0],
        'L1:Q4:SetDacCurrentC': [-2.0, 2.0],
        'L1:Q5:SetDacCurrentC': [-2.0, 2.0],
        # steering RG2
        'L1:V1:SetDacCurrentC': [-2.0, 2.0],
        'L1:V2:SetDacCurrentC': [-2.0, 2.0],
        'L1:V3:SetDacCurrentC': [-2.0, 2.0],
        'L1:H1:SetDacCurrentC': [-2.0, 2.0],
        'L1:H2:SetDacCurrentC': [-2.0, 2.0],
        # L2 steering
        'L2:SC1:HZ:PS:setCurrentAO':[ -2.0 ,2.0],  
        'L2:SC1:VL:PS:setCurrentAO':[ -2.0 ,2.0], 
        'L2:SC2:HZ:PS:setCurrentAO':[ -2.0 ,2.0], 
        'L2:SC2:VL:PS:setCurrentAO':[ -2.0 ,2.0], 
        'L2:SC3:HZ:PS:setCurrentAO':[ -2.0 ,2.0], 
        'L2:SC3:VL:PS:setCurrentAO':[ -2.0 ,2.0], 
        'L2:SC4:HZ:PS:setCurrentAO':[ -2.0 ,2.0], 
        'L2:SC4:VL:PS:setCurrentAO':[ -2.0 ,2.0],
        # alpha magnet
        'L1:RG2:LFA:CurrentAO':[1.30e+02,1.45e+02],
        # phase L1
        'L1:PP:phaseAdjAO':[6.0e+00,1.0e+01],
    }

    observables = ['L1:CM1:measCurrentCM','L3:CM1:measCurrentCM','L5:CM1:measCurrentCM' ]  # measurements
    TEST_RUN: bool =  False
    trim_delay: float = 8.0
    max_attempts: int = 10
    required_successful_readings: int = 5
    sleep_time: float = 0.5

    # test values before reading
    _test_variables = {'L1:RG2:KIK:chargeTrigC' : [0.5,1.0]}
    def get_variables(self,variable_names):
        """
        input is a list
        get pvs but first check if the conditons are met
        need to implement a method to check if the channel is connected 
        """
        epics.ca.clear_cache()
        channels = pva.MultiChannel(variable_names, pva.CA)
        get_value = [v[0]['value'] for v in channels.get().toDict()['value']]
        del channels
        return {variable_names[k]: get_value[k] for k in range(len(variable_names))}


    def set_variables(self,variable_inputs: dict[str, float]):
        """
        Set PVs and verify their values.

        Parameters:
            variable_inputs (dict[str, float]): A dictionary mapping PV names to values.

        Raises:
            Exception: If the values could not be set after retries.
        """ 
        epics.ca.clear_cache()
        #TEST_RUN = False
        if self.TEST_RUN:
            return None
        else:
            pass
        values =  list(variable_inputs.values())
        channels = pva.MultiChannel(list(variable_inputs.keys()), pva.CA)
        channels.putAsDoubleArray(values)
        verify = False
        sleep(self.trim_delay)
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
            del channels
            #return new_values
        else:
            del channels
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
        epics.ca.clear_cache()

        observed_values_list = []

        # Initialize channels for observables outside the loop
        channels = pva.MultiChannel(observable_names, pva.CA)

        for attempt in range(self.max_attempts):
            conditions = True
            # Check test conditions
            for key, (min_val, max_val) in self._test_variables.items():
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
                print (f'acquired {len(observed_values_list)} reading(s)')
                if len(observed_values_list) >= self.required_successful_readings:
                    # Required number of successful readings collected
                    break
            # Sleep before the next attempt
            sleep(self.sleep_time)
        
        if len(observed_values_list) >= self.required_successful_readings:
            # Compute the average across successful readings
            observed_values_over_time = np.array(observed_values_list)
            averaged_values = np.average(observed_values_over_time, axis=0)
            std_values = np.std(observed_values_over_time, axis=0)
            print (f'obtained averaged_values {averaged_values} and sigma {std_values} ')
            del channels
            return {observable_names[k]: averaged_values[k] for k in range(len(observable_names))}

        else:
            # Insufficient successful readings collected
            print('Insufficient successful readings after 10 attempts. Returning zero values.')
            del channels
            return {observable_name: np.nan for observable_name in observable_names} 


