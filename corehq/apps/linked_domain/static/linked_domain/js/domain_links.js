hqDefine("linked_domain/js/domain_links", [
    'jquery.rmi/jquery.rmi',
    'hqwebapp/js/initial_page_data',
    'underscore',
    'knockout',
    'hqwebapp/js/alert_user',
    'hqwebapp/js/multiselect_utils',
], function (
    RMI,
    initialPageData,
    _,
    ko,
    alert_user,
    multiselectUtils
) {
    var _private = {};
    _private.RMI = function () {};

    var ModelStatus = function (data) {
        var self = {};
        self.type = data.type;
        self.name = data.name;
        self.last_update = ko.observable(data.last_update);
        self.detail = data.detail;
        self.showPush = ko.observable(self.type == 'app');
        self.showUpdate = ko.observable(data.can_update);
        self.update_url = null;

        if (self.type === 'app' && self.detail && self.detail.app_id) {
            self.update_url = initialPageData.reverse('app_settings', self.detail.app_id);
        }
        self.hasError = ko.observable(false);
        self.hasSuccess = ko.observable(false);
        self.showSpinner = ko.observable(false);

        self.update = function () {
            self.showSpinner(true);
            self.showUpdate(false);
            _private.RMI("update_linked_model", {"model": {
                'type': self.type,
                'detail': self.detail,
            }}).done(function (data) {
                self.last_update(data.last_update);
                self.hasSuccess(true);
                self.showSpinner(false);
            })
                .fail(function () {
                    self.hasError(true);
                    self.showSpinner(false);
                });
        };

        return self;
    };

    var DomainLinksViewModel = function (data) {
        var self = {};
        self.domain = data.domain;
        self.master_link = data.master_link;
        if (self.master_link) {
            if (self.master_link.is_remote) {
                self.master_href = self.master_link.master_domain;
            } else {
                self.master_href = initialPageData.reverse('domain_links', self.master_link.master_domain);
            }
        }

        self.can_update = data.can_update;
        self.models = data.models;

        self.model_status = _.map(data.model_status, ModelStatus);

        self.linked_domains = ko.observableArray(_.map(data.linked_domains, function (link) {
            return DomainLink(link);
        }));

        self.deleteLink = function (link) {
            _private.RMI("delete_domain_link", {"linked_domain": link.linked_domain()})
                .done(function () {
                    self.linked_domains.remove(link);
                })
                .fail(function () {
                    alert_user.alert_user(gettext('Something unexpected happened.\n' +
                        'Please try again, or report an issue if the problem persists.'), 'danger');
                });
        };

        return self;
    };

    var DomainLink = function (link) {
        var self = {};
        self.linked_domain = ko.observable(link.linked_domain);
        self.is_remote = link.is_remote;
        self.master_domain = link.master_domain;
        self.remote_base_url = ko.observable(link.remote_base_url);
        self.last_update = link.last_update;
        if (self.is_remote) {
            self.domain_link = self.linked_domain;
        } else {
            self.domain_link = initialPageData.reverse('domain_links', self.linked_domain());
        }
        return self;
    };

    var setRMI = function (rmiUrl, csrfToken) {
        var _rmi = RMI(rmiUrl, csrfToken);
        _private.RMI = function (remoteMethod, data) {
            return _rmi("", data, {headers: {"DjNg-Remote-Method": remoteMethod}});
        };
    };

    $(function () {
        var view_data = initialPageData.get('view_data');
        var csrfToken = $("#csrfTokenContainer").val();
        setRMI(initialPageData.reverse('linked_domain:domain_link_rmi'), csrfToken);

        var model = DomainLinksViewModel(view_data);
        $("#domain_links").koApplyBindings(model);

        multiselectUtils.createFullMultiselectWidget(
            'select-push-domains',
            gettext("All projects"),
            gettext("Projects to push to"),
            gettext("Search projects"),
        );
        multiselectUtils.createFullMultiselectWidget(
            'select-push-models',
            gettext("All content"),
            gettext("Content to release"),
            gettext("Search content"),
        );

        $("#push-button").click(function () {
            // TODO: require at least one project
            // TODO: require at least one model
            // TODO: disable and reenable the button
            _private.RMI("create_release", {
                "models": $("#select-push-models").val(),
                "linked_domains": $("#select-push-domains").val(),
            }).done(function (data) {
                    alert_user.alert_user(data.message, data.success ? 'success' : 'danger');
            }).fail(function () {
                    alert_user.alert_user(gettext('Something unexpected happened.\n' +
                        'Please try again, or report an issue if the problem persists.'), 'danger');
            });
        });
    });
});
