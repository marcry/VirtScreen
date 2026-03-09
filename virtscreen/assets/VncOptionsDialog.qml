import QtQuick 2.10
import QtQuick.Controls 2.3
import QtQuick.Controls.Material 2.3
import QtQuick.Layouts 1.3

Dialog {
    title: "VNC Options"
    focus: true
    modal: true
    visible: true
    standardButtons: Dialog.Ok
    x: (parent ? (parent.width - width) / 2 : 0)
    y: (parent ? (parent.width - height) / 2 : 0)
    width: (parent && parent.popupWidth) ? parent.popupWidth : 360
    height: 350

    Component.onCompleted: {
        // Use injected 'appData' instead of performing local XHR.
        var data = (appData && appData.x11vncOptions) ? appData.x11vncOptions : {};
        // merge data and settings
        for (var key in data) {
            Object.assign(data[key], settings.x11vncOptions[key]);
        }
        var repeater = vncOptionsRepeater;
        repeater.model = Object.keys(data).map(function(k){return data[k]});
    }

    ColumnLayout {
        anchors.fill: parent
        RowLayout {
            TextField {
                id: vncCustomArgsTextField
                enabled: vncCustomArgsCheckbox.checked
                Layout.fillWidth: true
                placeholderText: "Custom x11vnc arguments"
                onTextEdited: {
                    settings.customX11vncArgs.value = text;
                }
                text: vncCustomArgsCheckbox.checked ? settings.customX11vncArgs.value : ""
            }
            CheckBox {
                id: vncCustomArgsCheckbox
                checked: settings.customX11vncArgs.enabled
                onToggled: {
                    settings.customX11vncArgs.enabled = checked;
                }
            }
        }
        ColumnLayout {
            enabled: !vncCustomArgsCheckbox.checked
            Repeater {
                id: vncOptionsRepeater
                RowLayout {
                    enabled: modelData.available
                    Label {
                        Layout.fillWidth: true
                        text: modelData.description + ' (' + modelData.value + ')' 
                    }
                    Switch {
                        checked: modelData.available ? modelData.enabled : false
                        onCheckedChanged: {
                            settings.x11vncOptions[modelData.value].enabled = checked;
                        }
                    }
                }
            }
        }
        RowLayout {
            // Empty layout
            Layout.fillHeight: true
        }
    }
    onAccepted: {}
    onRejected: {}
}
