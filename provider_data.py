import csv, requests, json
import numpy as np
import time

url = 'https://npiregistry.cms.hhs.gov/api/'
translation_dictionary = {'NPI':'number', 'taxonomy_id':'code', 'Description':'desc'}

class Data:
    def __init__(self, filename = None):
        self.headers = []
        self.data = None
        self.headerTocol = {}
        if filename:
            self.read(filename)

    def read(self, filename):
        '''
        Opens the file and stores all of the data in a Numpy Matrix and the headers as a list with Dictionary
        mapping to the columns of data
        :param filename: name of file to open
        :return: None
        '''
        data_list = []
        with open(filename, mode='rU') as fp:
            csv_reader = csv.reader(fp)
            self.headers = next(csv_reader)
            for line in csv_reader:
                data_list.append(line)
            for i in range(len(self.headers)):
                self.headers[i] = self.headers[i].strip()
                self.headerTocol[self.headers[i]] = i
            self.data = np.matrix(data_list)

    def get_num_dimensions(self):
        '''
        :return: Number of columns of data
        '''
        return self.data.shape[1]

    def get_num_points(self):
        '''
        :return: Number of data points
        '''
        return self.data.shape[0]

    def get_row(self, rowIndex):
        '''
        :param rowIndex: Index within matrix of desired data
        :return: a particular data point
        '''
        return self.data[rowIndex]

    def get_value(self, header, rowIndex):
        '''
        :param header: column header
        :param rowIndex: row of data
        :return: an individual aspect of a data point
        '''
        if header not in self.headerTocol.keys():
            return None
        return (self.data[rowIndex,self.headerTocol[header]])

    def get_data(self, headersInclude = []):
        '''
        :param headersInclude: List of headers for desired query columns
        :return: Columns of data
        '''
        if headersInclude == []:
            return
        matrix = []
        for h in headersInclude:
            list = []
            for i in range(self.get_num_points()):
                list.append([self.get_value(h, i)])
            matrix.append(np.matrix(list))
        return np.hstack(matrix.copy())



    def query(self,  search_concepts = (), populate_concepts = ()):
        '''
        :param search_concepts: List of concepts that are the criterium for the search
        :param populate_concepts: List of concepts that are desired to be populated
        :return: None. Updates data matrix to include column of query data
        '''
        # Build translation dictioary between NPPES database and OHDSI
        translation_keys = translation_dictionary.keys()
        for concept in search_concepts:
            if concept not in translation_keys:
                translation_dictionary[concept] = concept
        for concept in populate_concepts:
            if concept not in translation_keys:
                translation_dictionary[concept] = concept
        # Add all the columns of data to the matrix if the concepts to populate not already present in matrix
        for col_header in range(len(list(populate_concepts))):
            if populate_concepts[col_header] not in self.headers:
                null_column = []
                for i in range(self.get_num_points()):
                    null_column.append('')
                self.data = np.hstack((self.data, np.asmatrix(null_column).T))
                self.headers.append(populate_concepts[col_header])
                self.headerTocol[populate_concepts[col_header]] = len(self.headers)-1
        search_criterium = self.get_data(search_concepts)


        for i in range( self.get_num_points() ):
            print (i)
            criteria_dictionary = {}
            # Creates a dictionary which is used as parameters for the search for each individual provider
            for criteria in range ( search_criterium.shape[1] ):
                criteria_dictionary[translation_dictionary[search_concepts[criteria]]] \
                    = self.get_value(search_concepts[criteria], i)

            # Exclusion Criteria to speed up runs
            if '' in criteria_dictionary.values() or criteria_dictionary.values() == '0':
                continue

            var = False
            for c in populate_concepts:
                if self.get_value(c, i) != '':
                    var = True
            if var:
                continue
            # End Exclusion
            # Scrape
            r = json.loads(requests.get(url, params=criteria_dictionary).content)

            #Loads Person information as multi-level dictionary
            if 'results' in r.keys() and r['result_count'] == 1:
                # Limit to Columbia Area Doctors
                # address = r['results'][0]['addresses'][0]['state']
                # if address != 'CT' or address != 'NY' or address != 'NJ':
                #     continue
                taxon = r['results'][0]['taxonomies']
                for t in taxon:
                    if t['primary'] == True or len(taxon) == 1: # Finds Primary Taxonomy
                        for concept in range(len(populate_concepts)):
                            if populate_concepts[concept] == '':
                                # Allows for lookup by NPI and lookup NPI and populates matrix in place
                                self.data[i, self.headerTocol[populate_concepts[concept]]] = r['results'][0]['number']
                                continue
                            self.data[i,self.headerTocol[populate_concepts[concept]]] = \
                                    t[translation_dictionary[populate_concepts[concept]]]

    def test(self, parameter):
        '''
        :param parameter: Column name of data want to inspect
        :return: Number in that column that are not NULL
        '''
        d = self.get_data([parameter])
        i = 0
        for j in range( self.get_num_points()):
            if d[j,0] == None:
                i += 1
        print (str(parameter),': ',i, 'out of',self.get_num_points())


    def split_names(self):
        '''
        :return: Edits database to split provider_name column in to last_name and first_name columns
        '''
        names = self.get_data(['provider_name'])
        first_name = []
        last_name = []
        for i in range(self.get_num_points()):
            name = names[i,0].split(',')
            last_name.append(name[0])
            first_name.append(name[1])
        self.data = np.hstack((self.data[:,0],np.asmatrix(last_name).T,np.asmatrix(first_name).T,self.data[:,2:]))
        self.headers = [self.headers[0]] + ['last_name', 'first_name'] + self.headers[2:]
        for i in range(len(self.headers)):
            self.headerTocol[self.headers[i]] = i

    def write(self, filename=None, headers=None):
        '''
        :param filename: Name of new file
        :param headers: Headers of columns of data to include in new file
        :return:
        '''
        with open(filename, 'w') as fp:
            csv_writer = csv.writer(fp)
            if headers == None:
                csv_writer.writerow(self.headers)
            else:
                csv_writer.writerow(headers)
            data = np.asarray(self.data)
            for row in range(self.data.shape[0]):
                csv_writer.writerow(data[row])

if __name__ == "__main__":

    # Run 1
    # data = Data('ProviderTable.csv')
    # data.query(['NPI'], ['taxonomy_id'])
    # data.write('ProviderTableWithCodes1.csv')
    # exit(-1)

    # Run 2
    # data = Data('ProviderTableWithCodes.csv')
    # data.split_names()
    # data.query(['last_name', 'first_name'], ['NPI', 'taxonomy_id'])
    # data.write('ProviderTableWithCodesFromNames1.csv')
    # exit(-1)


    # Test to confirm all data exists
    # data = Data('ProviderTableWithCodesFromNames1.csv')
    # data.query(['NPI'], ['taxonomy_id'])
    # data.test('NPI')
    # data.test('taxonomy_id')

    # data = Data('CD_NPI.csv')
    # data.query(search_concepts=['NPI'], populate_concepts=['taxonomy_id','Description'])
    # data.write('CD_NPI_with_taxonomy.csv')

    data = Data('CD_NPI_with_taxonomy.csv')
    data.query(search_concepts=['NPI'], populate_concepts=['taxonomy_id','Description'])
    data.write('CD_NPI_with_taxonomy1.csv')
