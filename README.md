
# emporia VUE

This is a node server to pull energy meter data from the emporia VUE servers and make it
available to a [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY)
[Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with 
Polyglot V3 running on a [Polisy](https://www.universal-devices.com/product/polisy/)

(c) 2021 Robert Paauwe

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. From the Polyglot dashboard, select the emporia VUE node server and configure (see configuration options below).
4. Once configured, the emporia VUE node server should update the ISY with the proper nodes and begin filling in the node data.
5. Restart the Admin Console so that it can properly display the new node server nodes.

### Node Settings
The settings for this node are:

#### Short Poll
   * How often to poll for current energy data (in seconds)
#### Long Poll
   * How often to poll for daily energy data (in seconds)
#### Custom Parameters
	* username - your emporia VUE account user name
	* password - your emporia VUE account password

## Node substitution variables
### Controller node
 * sys.node.[address].ST      (Node sever online)
 * sys.node.[address].TWP     (Instetaneous power)



## Requirements
1. Polyglot V3.
2. ISY firmware 5.3.x or later

# Release Notes

- 1.0.1 07/29/2021
   - Use newer udi_interface and testing
- 1.0.0 05/24/2021
   - Initial version.
