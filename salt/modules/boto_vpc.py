# -*- coding: utf-8 -*-
'''
Connection module for Amazon VPC

.. versionadded:: Helium

:configuration: This module accepts explicit autoscale credentials but can also
    utilize IAM roles assigned to the instance trough Instance Profiles.
    Dynamic credentials are then automatically obtained from AWS API and no
    further configuration is necessary. More Information available at::

       http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html

    If IAM roles are not used you need to specify them either in a pillar or
    in the minion's config file::

        asg.keyid: GKTADJGHEIQSXMKKRBJ08H
        asg.key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

    A region may also be specified in the configuration::

        asg.region: us-east-1

    If a region is not specified, the default is us-east-1.

    It's also possible to specify key, keyid and region via a profile, either
    as a passed in dict, or as a string to pull from pillars or minion config:

        myprofile:
            keyid: GKTADJGHEIQSXMKKRBJ08H
            key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs
            region: us-east-1

:depends: boto
'''

# Import Python libs
import logging

log = logging.getLogger(__name__)

# Import third party libs
try:
    import boto
    import boto.vpc
    logging.getLogger('boto').setLevel(logging.CRITICAL)
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

from salt._compat import string_types


def __virtual__():
    '''
    Only load if boto libraries exist.
    '''
    if not HAS_BOTO:
        return False
    return True


def get_subnet_association(subnets, region=None, key=None, keyid=None,
                           profile=None):
    '''
    Given a subnet (aka: a vpc zone identifier) or list of subnets, returns
    vpc association.

    CLI example::

        a single subnet:
        salt myminion boto_vpc.get_subnet_association subnet-61b47516 region=us-east-1

        multiple subnets:
        salt myminion boto_vpc.get_subnet_association ['subnet-61b47516','subnet-2cb9785b'] region=us-east-1

        return values are:
        False - if an error occurs or if given subnets are associated with multiple vpcs
        VPC ID - if all given subnets are associated with one vpc
    '''
    conn = _get_conn(region, key, keyid, profile)
    if not conn:
        return False
    try:
        # subnet_ids=subnets can accept either a string or a list
        subnets = conn.get_all_subnets(subnet_ids=subnets)
    except boto.exception.BotoServerError as e:
        log.debug(e)
        return False
    # using a set to store vpc_ids - the use of set prevents duplicate
    # vpc_id values
    vpc_ids = set()
    for subnet in subnets:
        log.debug('examining subnet id: {0} for vpc_id'.format(subnet.id))
        if subnet in subnets:
            log.debug('subnet id: {0} is associated with vpc id: {1}'
                      .format(subnet.id, subnet.vpc_id))
            vpc_ids.add(subnet.vpc_id)
    if len(vpc_ids) == 1:
        vpc_id = vpc_ids.pop()
        log.debug('all subnets are associated with vpc id: {0}'.format(vpc_id))
        return vpc_id
    else:
        log.debug('given subnets are associated with fewer than 1 or greater'
                  ' than 1 subnets')
        return False


def exists(vpc_id, region=None, key=None, keyid=None, profile=None):
    '''
    Given a vpc id, check to see if the given vpc exists.

    CLI example::

        salt myminion boto_vpc.exists myvpc region=us-east-1
    '''
    conn = _get_conn(region, key, keyid, profile)
    if not conn:
        return False
    try:
        conn.get_all_vpcs(vpc_ids=[vpc_id])
        return True
    except boto.exception.BotoServerError as e:
        log.debug(e)
        return False


def _get_conn(region, key, keyid, profile):
    '''
    Get a boto connection to vpc.
    '''
    if profile:
        if isinstance(profile, string_types):
            _profile = __salt__['config.option'](profile)
        elif isinstance(profile, dict):
            _profile = profile
        key = _profile.get('key', None)
        keyid = _profile.get('keyid', None)
        region = _profile.get('region', None)

    if not region and __salt__['config.option']('vpc.region'):
        region = __salt__['config.option']('vpc.region')

    if not region:
        region = 'us-east-1'

    if not key and __salt__['config.option']('vpc.key'):
        key = __salt__['config.option']('vpc.key')
    if not keyid and __salt__['config.option']('vpc.keyid'):
        keyid = __salt__['config.option']('vpc.keyid')

    try:
        conn = boto.vpc.connect_to_region(region, aws_access_key_id=keyid,
                                          aws_secret_access_key=key)
    except boto.exception.NoAuthHandlerFound:
        log.error('No authentication credentials found when attempting to'
                  ' make boto autoscale connection.')
        return None
    return conn
