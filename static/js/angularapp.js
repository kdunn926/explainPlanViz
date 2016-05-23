var app = angular.module('myApp', []);

app.filter('split', function() {
    return function(input, splitChar) {
        // do some bounds checking here to ensure it has that index
        return input.split(splitChar);
    }
});

app.directive('bsDropdown', function ($compile) {
    return {
        restrict: 'E',
        //scope: true,
        scope: {
            items: '=dropdownData',
            doSelect: '&selectVal',
            selectedItem: '=preselectedItem'
        },
        link: function (scope, element, attrs) {
            var html = '';
            switch (attrs.menuType) {
                case "button":
                    html += '<div class="btn-group"><button class="btn button-label btn-info">' + scope.selectedItem + '</button><button class="btn btn-info dropdown-toggle" data-toggle="dropdown"><span class="caret"></span></button>';
                    break;
                default:
                    html += '<div class="dropdown"><a class="dropdown-toggle" role="button" data-toggle="dropdown"  href="javascript:;">Dropdown<b class="caret"></b></a>';
                    break;
            }
            html += '<ul class="dropdown-menu"><li ng-repeat="item in items" ><a tabindex="-1" data-ng-click="selectVal(item)">{{item}}</a></li></ul></div>';
            element.append($compile(html)(scope));
            //scope.bSelectedItem = scope.selectedItem;
            for (var i = 0; i < scope.items.length; i++) {
                if (scope.items[i] === scope.selectedItem) {
                    scope.bSelectedItem = scope.items[i];
                    break;
                }
            }
            // Function to handle changing roles
            scope.selectVal = function (item) {
                //alert("You chose " + role);
                switch (attrs.menuType) {
                    case "button":
                        $('button.button-label', element).html(item);
                        break;
                    default:
                        $('a.dropdown-toggle', element).html('<b class="caret"></b> ' + item);
                        break;
                }
                //scope.model.selected.role = item;
                //attrs.selectedItem = item;
                scope.doSelect({
                    selectedVal: item
                });
            };
            // Initialize the role
            scope.selectVal(scope.bSelectedItem);
        }
    };
});
app.controller("myCtrl", function($scope, $filter) {
    $scope.hoststring = "host1.pivotal.priv\nhost2.pivotal.priv\nhost3.pivotal.priv";
    $scope.newRole = "Datanode";
    $scope.newFqdn = "newhost.pivotal.priv";
    $scope.makeHost = function(hoststring) {
        var hostObjectList = [];
        angular.forEach($filter('split')(hoststring, '\n'), function(value, key) {
            hostObjectList.push({ id: key, fqdn: value, role: "Datanode" });
        });
        return hostObjectList;
    };
    $scope.model = { hosts: [] , selected: {} }
    $scope.model.hosts = $scope.makeHost($scope.hoststring);
    $scope.hosts = $scope.makeHost($scope.hoststring);
    $scope.roles = ["Datanode", "Admin node", "Edge node"];
    $scope.clusterTypes = ["3-node: Admin + 2 DN", "5-node: Admin, Edge + 3 DN", "N-node: Admin, Edge + (N-2) DN"];
    $scope.selectedCluster = "3-node (Admin + 2 DN)";
    $scope.ambariServer = "somewhere.pivotal.priv:8080"

    $scope.update = function() {
        $scope.model.hosts = $scope.makeHost($scope.hoststring); 
    };

    // gets the template to ng-include for a table row / item
    $scope.getTemplate = function (host) {
        if (host.id === $scope.model.selected.id) return 'edit';
        else return 'display';
    };

    $scope.editHost = function (idx) {
        $scope.model.selected = angular.copy($scope.model.hosts[idx]);
    };

    $scope.saveHost = function (idx) {
        console.log("Saving host " + idx + " " + $scope.model.selected.role);
        $scope.model.hosts[idx] = angular.copy($scope.model.selected);
        $scope.reset();
    };

    $scope.addHost = function(){     
        var newIdx = $scope.model.hosts.length;
        $scope.model.hosts.push({ 'id': newIdx, 'fqdn':$scope.newFqdn, 'role': $scope.newRole });
        $scope.hoststring = $scope.hoststring + "\n" + $scope.newFqdn ;
        $scope.newFqdn = "newhost" + (newIdx + 1) + ".pivotal.priv";
        $scope.newRole = "Datanode";
    };

    $scope.removeHost = function(index){              
        $scope.model.hosts.splice( index, 1 );        
        $scope.hoststring = "";
        angular.forEach($scope.model.hosts, function(value, key) {
            if ($scope.hoststring == "") {
                $scope.hoststring = value.fqdn;
            }
            else {
                $scope.hoststring = $scope.hoststring + "\n" +  value.fqdn;
            }
        });
        $scope.update();
    };

    $scope.reset = function () {
        $scope.model.selected = {};
    };

});

